# routes/journal_routes.py

import numpy as np
from itertools import combinations
    
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, JournalEntry, User, Profile, Strategy
from sqlalchemy import desc, asc, func, or_, extract
import os
from flask import Blueprint, request, jsonify, send_file, Response, send_from_directory
import json
import uuid
import yfinance as yf
from datetime import datetime, timedelta, date
import pandas as pd
from datetime import datetime, timedelta, timezone, date
import math
import io
import openai
import json
import numpy as np
from peewee import fn
import traceback

# Try to import scipy for advanced metrics, but don't fail if not available
try:
    from scipy.stats import linregress
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("Warning: scipy not available. Advanced metrics (K-Ratio, Z-Score) will be disabled.")

from models import db, JournalEntry, ImportBatch

# Initialize the Blueprint
journal_bp = Blueprint('journal', __name__)

def get_active_profile_id(user_id):
    """Get the active profile ID for a user"""
    active_profile = Profile.query.filter_by(user_id=user_id, is_active=True).first()
    if not active_profile:
        # Create a default profile if none exists
        default_profile = Profile(
            user_id=user_id,
            name="Default Profile",
            description="Default trading profile",
            is_active=True,
            mode="backtest"
        )
        db.session.add(default_profile)
        db.session.commit()
        return default_profile.id
    return active_profile.id

def build_group_aware_query(user_id, profile_id=None):
    """
    Build a query that handles both individual and group accounts.
    For group accounts, includes all group members' data.
    For individual accounts, includes only their own data.
    """
    current_user = User.query.get(user_id)
    if not current_user:
        print(f"❌ User {user_id} not found")
        return JournalEntry.query.filter_by(user_id=-1)  # Return empty query
    
    print(f"🔍 Building query for user {user_id} (account_type: {current_user.account_type}, group_id: {current_user.group_id})")
    
    if current_user.account_type == 'group' and current_user.group_id:
        # Group account: include trades from all group members
        group_members = User.query.filter_by(
            group_id=current_user.group_id,
            account_type='individual'
        ).all()
        user_ids = [member.id for member in group_members]
        
        print(f"👥 Group {current_user.group_id} has {len(user_ids)} individual members: {user_ids}")
        
        if user_ids:
            query = JournalEntry.query.filter(JournalEntry.user_id.in_(user_ids))
            if profile_id:
                query = query.filter_by(profile_id=profile_id)
                print(f"📊 Group query with profile_id: {profile_id}")
            else:
                print(f"📊 Group query without profile filter")
            return query
        else:
            # No group members found, but let's check if there are any users in this group at all
            all_group_users = User.query.filter_by(group_id=current_user.group_id).all()
            print(f"⚠️ No individual members found in group {current_user.group_id}, but found {len(all_group_users)} total users")
            
            if all_group_users:
                # Include all users in the group, regardless of account type
                all_user_ids = [user.id for user in all_group_users]
                print(f"🔄 Using all group users: {all_user_ids}")
                query = JournalEntry.query.filter(JournalEntry.user_id.in_(all_user_ids))
                if profile_id:
                    query = query.filter_by(profile_id=profile_id)
                return query
            else:
                print(f"❌ No users found in group {current_user.group_id}")
                return JournalEntry.query.filter_by(user_id=-1)
    else:
        # Individual account: show only their own trades
        print(f"👤 Individual account query for user {user_id}")
        query = JournalEntry.query.filter_by(user_id=user_id)
        if profile_id:
            query = query.filter_by(profile_id=profile_id)
            print(f"📊 Individual query with profile_id: {profile_id}")
        else:
            print(f"📊 Individual query without profile filter")
        return query

def analyze_variable_combinations(entries, combination_level=2, min_trades=5, selected_combinations=None):
    """
    Analyze combinations of variable VALUES to find the best performing combinations.
    
    Args:
        entries: List of journal entries
        combination_level: Number of variables to combine (2-5)
        min_trades: Minimum number of trades required for a combination
        selected_combinations: List of specific combinations to analyze
    
    Returns:
        tuple: (combinations_result, total_combinations_before_filter)
    """
    print(f"🔍 Debug - analyze_variable_combinations called with {len(entries)} entries")
    print(f"🔍 Debug - combination_level: {combination_level}, min_trades: {min_trades}")
    
    if not entries:
        print("🔍 Debug - No entries provided, returning empty result")
        return [], 0
    
    # Extract all unique variable-value combinations from entries
    variable_value_combinations = {}
    
    # Debug: Print sample variables to check encoding
    debug_count = 0
    entries_with_variables = 0
    for entry in entries:
        if debug_count < 3:
            variables_info = {}
            if hasattr(entry, 'variables') and entry.variables:
                variables_info['variables'] = entry.variables
                print(f"🔍 Debug - Entry {debug_count + 1} variables: {entry.variables} (type: {type(entry.variables)})")
            if hasattr(entry, 'extra_data') and entry.extra_data:
                variables_info['extra_data'] = entry.extra_data
                print(f"🔍 Debug - Entry {debug_count + 1} extra_data: {entry.extra_data} (type: {type(entry.extra_data)})")
            if variables_info:
                print(f"🔍 Debug - Entry {debug_count + 1}: {variables_info}")
                debug_count += 1
        
        # Count entries with variables
        if hasattr(entry, 'variables') and entry.variables:
            entries_with_variables += 1
        if hasattr(entry, 'extra_data') and entry.extra_data:
            entries_with_variables += 1

    print(f"🔍 Debug - Total entries: {len(entries)}, Entries with variables: {entries_with_variables}")
    
    for entry in entries:
        try:
            # Get variables from both variables and extra_data fields
            variables = {}
            if hasattr(entry, 'variables') and entry.variables:
                variables.update(entry.variables if isinstance(entry.variables, dict) else {})
            
            # Also check extra_data for custom variables (var1-var10)
            if hasattr(entry, 'extra_data') and entry.extra_data:
                extra_data = entry.extra_data if isinstance(entry.extra_data, dict) else {}
                # Add custom variables from extra_data to variables dict
                for key, value in extra_data.items():
                    if key.startswith('var') and value is not None:
                        variables[key] = value
            
            if not variables:
                continue
            
            print(f"🔍 Debug - Processing entry variables: {variables}")
            # Create a list of variable:value pairs with proper encoding handling
            var_value_pairs = []
            for var_name, var_value in variables.items():
                if var_value is not None:
                    # Handle different variable value formats
                    if isinstance(var_value, list):
                        # If it's a list, take the first value
                        if var_value and str(var_value[0]).strip():
                            var_value_pairs.append(f"{var_name}:{str(var_value[0]).strip()}")
                    elif isinstance(var_value, str) and var_value.strip():
                        var_value_pairs.append(f"{var_name}:{var_value.strip()}")
                    elif var_value:  # Handle other types
                        var_value_pairs.append(f"{var_name}:{str(var_value).strip()}")
            
            if len(var_value_pairs) >= 2:  # Need at least 2 variables for combinations
                # Generate combinations of variable:value pairs
                from itertools import combinations
                for i in range(2, min(combination_level + 1, len(var_value_pairs) + 1)):
                    for combo in combinations(var_value_pairs, i):
                        combo_key = '+'.join(sorted(combo))
                        if combo_key not in variable_value_combinations:
                            variable_value_combinations[combo_key] = []
                        variable_value_combinations[combo_key].append(entry)
                        
        except Exception as e:
            print(f"Error processing entry variables: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    if not variable_value_combinations:
        return [], 0
    
    total_combinations_before_filter = len(variable_value_combinations)
    
    # Filter combinations if specific ones are requested
    if selected_combinations:
        filtered_combinations = {}
        for combo_key, combo_trades in variable_value_combinations.items():
            if combo_key in selected_combinations:
                filtered_combinations[combo_key] = combo_trades
        variable_value_combinations = filtered_combinations
    
    # Analyze each combination
    results = []
    for combo_key, combo_trades in variable_value_combinations.items():
        # Skip if not enough trades
        if len(combo_trades) < min_trades:
            continue
        
        # Calculate metrics for this combination
        total_pnl = sum(trade.pnl for trade in combo_trades if trade.pnl is not None)
        winning_trades = [t for t in combo_trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in combo_trades if t.pnl and t.pnl < 0]
        
        win_rate = len(winning_trades) / len(combo_trades) * 100 if combo_trades else 0
        
        # Calculate profit factor
        total_wins = sum(t.pnl for t in winning_trades if t.pnl)
        total_losses = abs(sum(t.pnl for t in losing_trades if t.pnl))
        profit_factor = total_wins / total_losses if total_losses > 0 else (total_wins if total_wins > 0 else None)
        
        # Calculate average win and loss
        avg_win = round(total_wins / len(winning_trades), 2) if winning_trades else 0
        avg_loss = round(total_losses / len(losing_trades), 2) if losing_trades else 0
        
        results.append({
            'combination': combo_key,
            'combination_with_values': combo_key,  # Keep both for compatibility
            'trades': len(combo_trades),
            'pnl': round(total_pnl, 2),
            'win_rate': round(win_rate, 1),
            'profit_factor': round(profit_factor, 2) if profit_factor is not None else None,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_wins': round(total_wins, 2),
            'total_losses': round(total_losses, 2)
        })
    
    # Sort by profit factor (descending)
    results.sort(key=lambda x: x['profit_factor'] if x['profit_factor'] is not None else 0, reverse=True)
    
    print(f"Generated {len(results)} variable value combinations from {total_combinations_before_filter} total combinations")
    
    return results, total_combinations_before_filter

# Make sure uploads folder exists
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
SCREENSHOTS_FOLDER = os.path.join(UPLOAD_FOLDER, 'screenshots')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SCREENSHOTS_FOLDER, exist_ok=True)

# Configure OpenAI API Key
# Make sure to set the OPENAI_API_KEY environment variable
openai.api_key = os.environ.get("OPENAI_API_KEY", "")




@journal_bp.route('/list', methods=['GET'])
@jwt_required()
def list_entries():
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        
        # Get the current user to check account type
        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        # Build base query - handle group accounts differently
        if current_user.account_type == 'group' and current_user.group_id:
            # Group account: show trades from all group members
            group_members = User.query.filter_by(
                group_id=current_user.group_id,
                account_type='individual'
            ).all()
            user_ids = [member.id for member in group_members]
            
            if user_ids:
                query = JournalEntry.query.filter(
                    JournalEntry.user_id.in_(user_ids)
                ).order_by(JournalEntry.date.desc())
            else:
                # No group members found, return empty query
                query = JournalEntry.query.filter_by(user_id=-1)  # Non-existent user_id
        else:
            # Individual account: show only their own trades
            query = JournalEntry.query.filter_by(user_id=user_id, profile_id=profile_id).order_by(JournalEntry.date.desc())
        
        # Apply filters if provided
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        symbols = request.args.get('symbols')
        directions = request.args.get('directions')
        strategies = request.args.get('strategies')
        setups = request.args.get('setups')
        min_pnl = request.args.get('min_pnl')
        max_pnl = request.args.get('max_pnl')
        min_rr = request.args.get('min_rr')
        max_rr = request.args.get('max_rr')
        batch_ids = request.args.get('batch_ids')
        variables_param = request.args.get('variables')
        
        # Apply date filters
        if from_date:
            try:
                from_date = datetime.strptime(from_date, '%Y-%m-%d')
                query = query.filter(JournalEntry.date >= from_date)
            except ValueError:
                pass
                
        if to_date:
            try:
                to_date = datetime.strptime(to_date, '%Y-%m-%d')
                query = query.filter(JournalEntry.date <= to_date)
            except ValueError:
                pass
        
        # Apply symbol filter
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
            if symbol_list:
                query = query.filter(JournalEntry.symbol.in_(symbol_list))
        
        # Apply direction filter
        if directions:
            direction_list = [d.strip() for d in directions.split(',') if d.strip()]
            if direction_list:
                query = query.filter(JournalEntry.direction.in_(direction_list))
        
        # Apply strategy filter
        if strategies:
            strategy_list = [s.strip() for s in strategies.split(',') if s.strip()]
            if strategy_list:
                query = query.filter(JournalEntry.strategy.in_(strategy_list))
        
        # Apply setup filter
        if setups:
            setup_list = [s.strip() for s in setups.split(',') if s.strip()]
            if setup_list:
                query = query.filter(JournalEntry.setup.in_(setup_list))
        
        # Apply P&L range filters
        if min_pnl:
            try:
                min_pnl_val = float(min_pnl)
                query = query.filter(JournalEntry.pnl >= min_pnl_val)
            except ValueError:
                pass
        
        if max_pnl:
            try:
                max_pnl_val = float(max_pnl)
                query = query.filter(JournalEntry.pnl <= max_pnl_val)
            except ValueError:
                pass
        
        # Apply R:R range filters
        if min_rr:
            try:
                min_rr_val = float(min_rr)
                query = query.filter(JournalEntry.rr >= min_rr_val)
            except ValueError:
                pass
        
        if max_rr:
            try:
                max_rr_val = float(max_rr)
                query = query.filter(JournalEntry.rr <= max_rr_val)
            except ValueError:
                pass
        
        # Apply import batch filter
        if batch_ids:
            try:
                batch_id_list = [int(b.strip()) for b in batch_ids.split(',') if b.strip()]
                if batch_id_list:
                    query = query.filter(JournalEntry.import_batch_id.in_(batch_id_list))
            except ValueError:
                pass
        
        # Get filtered entries
        entries = query.all()
        
        # Apply variables filter if provided (post-query filtering)
        if variables_param:
            try:
                variables_filter = json.loads(variables_param)
                if isinstance(variables_filter, dict) and variables_filter:
                    filtered_entries = []
                    for entry in entries:
                        matches_all = True
                        for var_name, var_values in variables_filter.items():
                            if not isinstance(var_values, list) or not var_values:
                                continue
                            
                            entry_vars = entry.variables or {}
                            if isinstance(entry_vars, dict):
                                entry_value = entry_vars.get(var_name)
                                if entry_value:
                                    if isinstance(entry_value, list):
                                        entry_values = [str(v).strip().lower() for v in entry_value if v]
                                    else:
                                        entry_values = [str(entry_value).strip().lower()]
                                else:
                                    extra_data = entry.extra_data or {}
                                    if isinstance(extra_data, dict):
                                        entry_value = extra_data.get(var_name)
                                        if entry_value:
                                            if isinstance(entry_value, list):
                                                entry_values = [str(v).strip().lower() for v in entry_value if v]
                                            else:
                                                entry_values = [str(entry_value).strip().lower()]
                                        else:
                                            entry_values = []
                                    else:
                                        entry_values = []
                            else:
                                entry_values = []
                            
                            filter_values = [str(v).strip().lower() for v in var_values if v]
                            if not any(ev in filter_values for ev in entry_values):
                                matches_all = False
                                break
                        
                        if matches_all:
                            filtered_entries.append(entry)
                    
                    entries = filtered_entries
            except (json.JSONDecodeError, TypeError):
                pass

        result = []
        for e in entries:
            result.append({
                'id': e.id,
                'symbol': e.symbol,
                'direction': e.direction,
                'entry_price': e.entry_price,
                'exit_price': e.exit_price,
                'quantity': e.quantity,
                'contract_size': e.contract_size,
                'instrument_type': e.instrument_type,
                'risk_amount': e.risk_amount,
                'pnl': e.pnl,
                'rr': e.rr,
                'notes': e.notes,
                'entry_screenshot': e.entry_screenshot,
                'exit_screenshot': e.exit_screenshot,
                'extra_data': e.extra_data or {},
                'variables': e.variables or {},  # 
                'date': e.date.isoformat(),
                'created_at': e.created_at.isoformat(),
                'updated_at': e.updated_at.isoformat()
            })

        return jsonify(result), 200

    except Exception as e:
        print(" list_entries error:", e)
        return jsonify({'error': str(e)}), 500

# routes/journal_routes.py

import numpy as np
from itertools import combinations
    
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, JournalEntry, User, Profile, Strategy
from sqlalchemy import desc, asc, func, or_, extract
import os
from flask import Blueprint, request, jsonify, send_file, Response, send_from_directory
import json
import uuid
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
from datetime import datetime, timedelta, timezone
import math
import io
import openai
import json
import numpy as np
from peewee import fn
import traceback

# Try to import scipy for advanced metrics, but don't fail if not available
try:
    from scipy.stats import linregress
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("Warning: scipy not available. Advanced metrics (K-Ratio, Z-Score) will be disabled.")

from models import db, JournalEntry, ImportBatch

# Initialize the Blueprint
journal_bp = Blueprint('journal', __name__)

@journal_bp.route('/add', methods=['POST'])
@jwt_required()
def add_entry():
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        data = request.get_json()
        print(f"🔍 Backend received data: {data}")
        print(f"🔍 Advanced fields in received data:")
        print(f"  high_price: {data.get('high_price')} (type: {type(data.get('high_price'))})")
        print(f"  low_price: {data.get('low_price')} (type: {type(data.get('low_price'))})")
        print(f"  stop_loss: {data.get('stop_loss')} (type: {type(data.get('stop_loss'))})")
        print(f"  take_profit: {data.get('take_profit')} (type: {type(data.get('take_profit'))})")
        print(f"  open_time: {data.get('open_time')} (type: {type(data.get('open_time'))})")
        print(f"  close_time: {data.get('close_time')} (type: {type(data.get('close_time'))})")
        print(f"🔍 Variables in received data:")
        print(f"  variables: {data.get('variables')} (type: {type(data.get('variables'))})")
        print(f"  extra_data: {data.get('extra_data')} (type: {type(data.get('extra_data'))})")

        required_fields = ['symbol', 'direction', 'entry_price', 'exit_price', 'quantity']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Parse the entry datetime if provided, otherwise use current time in UTC
        if data.get('entry_datetime') and isinstance(data['entry_datetime'], str):
            try:
                # The frontend sends a local datetime string (e.g., "YYYY-MM-DDTHH:MM")
                # This creates a naive datetime object, which is what we want for storing local time.
                trade_date = datetime.fromisoformat(data['entry_datetime'])
            except (ValueError, TypeError) as e:
                print(f"Error parsing entry_datetime '{data['entry_datetime']}': {e}")
                trade_date = datetime.now(timezone.utc) # Fallback to current UTC time on parsing error
        else:
            trade_date = datetime.now(timezone.utc) # Default to current UTC time if not provided

        # Parse commission, slippage, open_time, close_time
        commission = float(data['commission']) if data.get('commission') is not None else None
        slippage = float(data['slippage']) if data.get('slippage') is not None else None
        
        # Ensure variables are in the correct format
        variables = data.get('variables', {})
        print(f"🔍 Debug - Raw variables from frontend: {variables}")
        print(f"🔍 Debug - Variables type: {type(variables)}")
        
        if variables and isinstance(variables, dict):
            # Convert all variable values to lists if they aren't already
            formatted_variables = {}
            for var_name, var_values in variables.items():
                print(f"🔍 Debug - Processing variable {var_name}: {var_values} (type: {type(var_values)})")
                if isinstance(var_values, list):
                    formatted_variables[var_name] = var_values
                elif isinstance(var_values, str):
                    formatted_variables[var_name] = [var_values]
                else:
                    formatted_variables[var_name] = [str(var_values)]
            variables = formatted_variables
            print(f"🔍 Debug - Formatted variables: {variables}")
        else:
            variables = {}
            print(f"🔍 Debug - No variables or invalid format, using empty dict")
        
        # Parse open_time and close_time with flexible format support
        def parse_datetime_field(field_name, field_value):
            """Parse datetime field with support for various formats including minute-only"""
            if not field_value:
                return None
                
            print(f"Parsing {field_name}: '{field_value}'")
            value = str(field_value).strip()
            
            try:
                # Handle various datetime formats
                dt = None
                
                # Format 1: ISO format with T (e.g., "2024-06-01T10:00" or "2024-06-01T10:00:00")
                if 'T' in value:
                    # Remove timezone info if present and parse as local time
                    if 'Z' in value:
                        value = value.replace('Z', '')
                    elif '+' in value:
                        value = value.split('+')[0]
                    elif '-' in value and len(value.split('-')[-1]) <= 2:
                        # This is a date, not timezone
                        pass
                    else:
                        # Remove timezone offset if present
                        parts = value.split('-')
                        if len(parts) > 3:
                            value = '-'.join(parts[:3]) + 'T' + parts[3].split('+')[0].split('-')[0]
                    
                    # Add seconds if missing
                    if value.count(':') == 1:
                        value += ':00'
                    
                    dt = datetime.fromisoformat(value)
                
                # Format 2: Date and time separated by space (e.g., "2024-06-01 10:00")
                elif ' ' in value and len(value.split(' ')) == 2:
                    date_part, time_part = value.split(' ')
                    # Add seconds if missing
                    if time_part.count(':') == 1:
                        time_part += ':00'
                    value = f"{date_part}T{time_part}"
                    dt = datetime.fromisoformat(value)
                
                # Format 3: American format (e.g., "06/01/2024 10:00 AM")
                elif '/' in value and ('AM' in value.upper() or 'PM' in value.upper()):
                    # Parse American format
                    dt = datetime.strptime(value, '%m/%d/%Y %I:%M %p')
                
                # Format 4: European format (e.g., "01/06/2024 10:00")
                elif '/' in value and value.count('/') == 2:
                    # Try different European formats
                    try:
                        dt = datetime.strptime(value, '%d/%m/%Y %H:%M')
                    except ValueError:
                        try:
                            dt = datetime.strptime(value, '%m/%d/%Y %H:%M')
                        except ValueError:
                            dt = datetime.strptime(value, '%Y/%m/%d %H:%M')
                
                if dt is None:
                    raise ValueError(f"Unsupported datetime format: {field_value}")
                
                # Keep as local time (no timezone conversion)
                # The frontend sends local time, so we store it as local time
                if dt.tzinfo is None:
                    # Keep as naive datetime (local time)
                    pass
                
                print(f"  Successfully parsed {field_name}: {dt}")
                return dt
                
            except Exception as e:
                print(f"  ERROR parsing {field_name} '{field_value}': {e}")
                raise ValueError(f"Invalid datetime format for {field_name}: '{field_value}'. Supported formats: YYYY-MM-DDTHH:MM, MM/DD/YYYY HH:MM AM/PM, DD/MM/YYYY HH:MM")

        open_time = None
        close_time = None
        
        # Parse open_time
        if data.get('open_time'):
            try:
                open_time = parse_datetime_field('open_time', data['open_time'])
            except ValueError as ve:
                return jsonify({'error': str(ve)}), 400
                
        # Parse close_time
        if data.get('close_time'):
            try:
                close_time = parse_datetime_field('close_time', data['close_time'])
            except ValueError as ve:
                return jsonify({'error': str(ve)}), 400
        
        # Validate that close_time is after open_time if both are provided
        if open_time and close_time:
            if close_time <= open_time:
                return jsonify({'error': 'close_time must be after open_time'}), 400
            duration_seconds = (close_time - open_time).total_seconds()
            print(f"Trade duration: {duration_seconds} seconds ({duration_seconds/60:.1f} minutes)")

        entry = JournalEntry(
            user_id=user_id,
            profile_id=profile_id,
            symbol=data['symbol'],
            direction=data['direction'],
            entry_price=float(data['entry_price']) if data.get('entry_price') is not None and data['entry_price'] != '' else 0.0,
            exit_price=float(data['exit_price']) if data.get('exit_price') is not None and data['exit_price'] != '' else 0.0,
            stop_loss=float(data['stop_loss']) if data.get('stop_loss') is not None else None,
            take_profit=float(data['take_profit']) if data.get('take_profit') is not None else None,
            high_price=float(data['high_price']) if data.get('high_price') is not None else None,
            low_price=float(data['low_price']) if data.get('low_price') is not None else None,
            quantity=float(data['quantity']) if data.get('quantity') is not None and data['quantity'] != '' else 1.0,
            contract_size=(float(data['contract_size']) if data.get('contract_size') is not None else None),
            instrument_type=data.get('instrument_type', 'crypto'),
            risk_amount=(float(data['risk_amount']) if data.get('risk_amount') is not None else None),
            pnl=(float(data['pnl']) if data.get('pnl') is not None else None),
            rr=(float(data['rr']) if data.get('rr') is not None else None),
            notes=data.get('notes'),
            commission=commission,
            slippage=slippage,
            open_time=open_time,
            close_time=close_time,
            entry_screenshot=data.get('entry_screenshot'),
            exit_screenshot=data.get('exit_screenshot'),
            date=trade_date,  # Set the trade date
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            extra_data=data.get('extra_data', {}),
            variables=variables
        )
        db.session.add(entry)
        db.session.commit()
        
        print(f"💾 Saved to database:")
        print(f"  high_price: {entry.high_price}")
        print(f"  low_price: {entry.low_price}")
        print(f"  stop_loss: {entry.stop_loss}")
        print(f"  take_profit: {entry.take_profit}")
        print(f"  open_time: {entry.open_time}")
        print(f"  close_time: {entry.close_time}")
        print(f"  variables: {entry.variables}")
        print(f"  extra_data: {entry.extra_data}")
        print(f"  variables type: {type(entry.variables)}")
        print(f"  extra_data type: {type(entry.extra_data)}")
        
        # Also log what's being returned in the response
        print(f"📤 Response includes:")
        print(f"  high_price: {entry.high_price}")
        print(f"  low_price: {entry.low_price}")
        print(f"  stop_loss: {entry.stop_loss}")
        print(f"  take_profit: {entry.take_profit}")
        print(f"  open_time: {entry.open_time}")
        print(f"  close_time: {entry.close_time}")

        return jsonify({
            'trade': {
                'id': entry.id,
                'symbol': entry.symbol,
                'direction': entry.direction,
                'entry_price': entry.entry_price,
                'exit_price': entry.exit_price,
                'high_price': entry.high_price,
                'low_price': entry.low_price,
                'quantity': entry.quantity,
                'contract_size': entry.contract_size,
                'instrument_type': entry.instrument_type,
                'risk_amount': entry.risk_amount,
                'pnl': entry.pnl,
                'rr': entry.rr,
                'notes': entry.notes,
                'entry_screenshot': entry.entry_screenshot,
                'exit_screenshot': entry.exit_screenshot,
                'date': entry.date.isoformat(),
                'extra_data': entry.extra_data or {},
                'variables': entry.variables or {},
                'created_at': entry.created_at.isoformat(),
                'updated_at': entry.updated_at.isoformat()  
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        print(" add_entry error:", e)
        return jsonify({'error': str(e)}), 500

@journal_bp.route('/list', methods=['GET'])
@jwt_required()
def list_entries():
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        
        # Get the current user to check account type
        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        # Build base query - handle group accounts differently
        if current_user.account_type == 'group' and current_user.group_id:
            # Group account: show trades from all group members
            group_members = User.query.filter_by(
                group_id=current_user.group_id,
                account_type='individual'
            ).all()
            user_ids = [member.id for member in group_members]
            
            if user_ids:
                query = JournalEntry.query.filter(
                    JournalEntry.user_id.in_(user_ids)
                ).order_by(JournalEntry.date.desc())
            else:
                # No group members found, return empty query
                query = JournalEntry.query.filter_by(user_id=-1)  # Non-existent user_id
        else:
            # Individual account: show only their own trades
            query = JournalEntry.query.filter_by(user_id=user_id, profile_id=profile_id).order_by(JournalEntry.date.desc())
        
        # Apply filters if provided
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        symbols = request.args.get('symbols')
        directions = request.args.get('directions')
        strategies = request.args.get('strategies')
        setups = request.args.get('setups')
        min_pnl = request.args.get('min_pnl')
        max_pnl = request.args.get('max_pnl')
        min_rr = request.args.get('min_rr')
        max_rr = request.args.get('max_rr')
        batch_ids = request.args.get('batch_ids')
        variables_param = request.args.get('variables')
        
        # Apply date filters
        if from_date:
            try:
                from_date = datetime.strptime(from_date, '%Y-%m-%d')
                query = query.filter(JournalEntry.date >= from_date)
            except ValueError:
                pass
                
        if to_date:
            try:
                to_date = datetime.strptime(to_date, '%Y-%m-%d')
                query = query.filter(JournalEntry.date <= to_date)
            except ValueError:
                pass
        
        # Apply symbol filter
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
            if symbol_list:
                query = query.filter(JournalEntry.symbol.in_(symbol_list))
        
        # Apply direction filter
        if directions:
            direction_list = [d.strip() for d in directions.split(',') if d.strip()]
            if direction_list:
                query = query.filter(JournalEntry.direction.in_(direction_list))
        
        # Apply strategy filter
        if strategies:
            strategy_list = [s.strip() for s in strategies.split(',') if s.strip()]
            if strategy_list:
                query = query.filter(JournalEntry.strategy.in_(strategy_list))
        
        # Apply setup filter
        if setups:
            setup_list = [s.strip() for s in setups.split(',') if s.strip()]
            if setup_list:
                query = query.filter(JournalEntry.setup.in_(setup_list))
        
        # Apply P&L range filters
        if min_pnl:
            try:
                min_pnl_val = float(min_pnl)
                query = query.filter(JournalEntry.pnl >= min_pnl_val)
            except ValueError:
                pass
        
        if max_pnl:
            try:
                max_pnl_val = float(max_pnl)
                query = query.filter(JournalEntry.pnl <= max_pnl_val)
            except ValueError:
                pass
        
        # Apply R:R range filters
        if min_rr:
            try:
                min_rr_val = float(min_rr)
                query = query.filter(JournalEntry.rr >= min_rr_val)
            except ValueError:
                pass
        
        if max_rr:
            try:
                max_rr_val = float(max_rr)
                query = query.filter(JournalEntry.rr <= max_rr_val)
            except ValueError:
                pass
        
        # Apply import batch filter
        if batch_ids:
            try:
                batch_id_list = [int(b.strip()) for b in batch_ids.split(',') if b.strip()]
                if batch_id_list:
                    query = query.filter(JournalEntry.import_batch_id.in_(batch_id_list))
            except ValueError:
                pass
        
        # Get filtered entries
        entries = query.all()
        
        # Apply variables filter if provided (post-query filtering)
        if variables_param:
            try:
                variables_filter = json.loads(variables_param)
                if isinstance(variables_filter, dict) and variables_filter:
                    filtered_entries = []
                    for entry in entries:
                        matches_all = True
                        for var_name, var_values in variables_filter.items():
                            if not isinstance(var_values, list) or not var_values:
                                continue
                            
                            entry_vars = entry.variables or {}
                            if isinstance(entry_vars, dict):
                                entry_value = entry_vars.get(var_name)
                                if entry_value:
                                    if isinstance(entry_value, list):
                                        entry_values = [str(v).strip().lower() for v in entry_value if v]
                                    else:
                                        entry_values = [str(entry_value).strip().lower()]
                                else:
                                    extra_data = entry.extra_data or {}
                                    if isinstance(extra_data, dict):
                                        entry_value = extra_data.get(var_name)
                                        if entry_value:
                                            if isinstance(entry_value, list):
                                                entry_values = [str(v).strip().lower() for v in entry_value if v]
                                            else:
                                                entry_values = [str(entry_value).strip().lower()]
                                        else:
                                            entry_values = []
                                    else:
                                        entry_values = []
                            else:
                                entry_values = []
                            
                            filter_values = [str(v).strip().lower() for v in var_values if v]
                            if not any(ev in filter_values for ev in entry_values):
                                matches_all = False
                                break
                        
                        if matches_all:
                            filtered_entries.append(entry)
                    
                    entries = filtered_entries
            except (json.JSONDecodeError, TypeError):
                pass

        result = []
        for e in entries:
            result.append({
                'id': e.id,
                'symbol': e.symbol,
                'direction': e.direction,
                'entry_price': e.entry_price,
                'exit_price': e.exit_price,
                'high_price': e.high_price,
                'low_price': e.low_price,
                'stop_loss': e.stop_loss,
                'take_profit': e.take_profit,
                'open_time': e.open_time.strftime('%Y-%m-%dT%H:%M') if e.open_time else None,
                'close_time': e.close_time.strftime('%Y-%m-%dT%H:%M') if e.close_time else None,
                'quantity': e.quantity,
                'contract_size': e.contract_size,
                'instrument_type': e.instrument_type,
                'risk_amount': e.risk_amount,
                'pnl': e.pnl,
                'rr': e.rr,
                'notes': e.notes,
                'entry_screenshot': e.entry_screenshot,
                'exit_screenshot': e.exit_screenshot,
                'extra_data': e.extra_data or {},
                'variables': e.variables or {},  # 
                'date': e.date.isoformat(),
                'created_at': e.created_at.isoformat(),
                'updated_at': e.updated_at.isoformat()
            })

        return jsonify(result), 200

    except Exception as e:
        print(" list_entries error:", e)
        return jsonify({'error': str(e)}), 500

@journal_bp.route('/stats', methods=['GET'])
@jwt_required()
def stats():
    try:
        user_id_str = get_jwt_identity()
        user_id = int(user_id_str)
        profile_id = get_active_profile_id(user_id)

        # Get the current user to check account type
        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        # Build base query - handle group accounts differently
        if current_user.account_type == 'group' and current_user.group_id:
            # Group account: include trades from all group members
            group_members = User.query.filter_by(
                group_id=current_user.group_id,
                account_type='individual'
            ).all()
            user_ids = [member.id for member in group_members]
            
            if user_ids:
                query = JournalEntry.query.filter(
                    JournalEntry.user_id.in_(user_ids)
                ).order_by(JournalEntry.date.asc())
            else:
                # No group members found, return empty query
                query = JournalEntry.query.filter_by(user_id=-1)  # Non-existent user_id
        else:
            # Individual account: show only their own trades
            query = JournalEntry.query.filter_by(user_id=user_id, profile_id=profile_id).order_by(JournalEntry.date.asc())
        
        # Apply filters if provided
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        symbols = request.args.get('symbols')
        directions = request.args.get('directions')
        strategies = request.args.get('strategies')
        setups = request.args.get('setups')
        min_pnl = request.args.get('min_pnl')
        max_pnl = request.args.get('max_pnl')
        min_rr = request.args.get('min_rr')
        max_rr = request.args.get('max_rr')
        batch_ids = request.args.get('batch_ids')
        variables_param = request.args.get('variables')
        time_of_day = request.args.get('time_of_day')
        day_of_week = request.args.get('day_of_week')
        month = request.args.get('month')
        year = request.args.get('year')
        
        # Apply date filters
        if from_date:
            try:
                from_date = datetime.strptime(from_date, '%Y-%m-%d')
                query = query.filter(JournalEntry.date >= from_date)
            except ValueError:
                pass
                
        if to_date:
            try:
                to_date = datetime.strptime(to_date, '%Y-%m-%d')
                query = query.filter(JournalEntry.date <= to_date)
            except ValueError:
                pass
        
        # Apply symbol filter
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
            if symbol_list:
                query = query.filter(JournalEntry.symbol.in_(symbol_list))
        
        # Apply direction filter
        if directions:
            direction_list = [d.strip() for d in directions.split(',') if d.strip()]
            if direction_list:
                query = query.filter(JournalEntry.direction.in_(direction_list))
        
        # Apply strategy filter
        if strategies:
            strategy_list = [s.strip() for s in strategies.split(',') if s.strip()]
            if strategy_list:
                query = query.filter(JournalEntry.strategy.in_(strategy_list))
        
        # Apply setup filter
        if setups:
            setup_list = [s.strip() for s in setups.split(',') if s.strip()]
            if setup_list:
                query = query.filter(JournalEntry.setup.in_(setup_list))
        
        # Apply P&L range filters
        if min_pnl:
            try:
                min_pnl_val = float(min_pnl)
                query = query.filter(JournalEntry.pnl >= min_pnl_val)
            except ValueError:
                pass
        
        if max_pnl:
            try:
                max_pnl_val = float(max_pnl)
                query = query.filter(JournalEntry.pnl <= max_pnl_val)
            except ValueError:
                pass
        
        # Apply R:R range filters
        if min_rr:
            try:
                min_rr_val = float(min_rr)
                query = query.filter(JournalEntry.rr >= min_rr_val)
            except ValueError:
                pass
        
        if max_rr:
            try:
                max_rr_val = float(max_rr)
                query = query.filter(JournalEntry.rr <= max_rr_val)
            except ValueError:
                pass
        
        # Apply import batch filter
        if batch_ids:
            try:
                batch_id_list = [int(b.strip()) for b in batch_ids.split(',') if b.strip()]
                if batch_id_list:
                    query = query.filter(JournalEntry.import_batch_id.in_(batch_id_list))
            except ValueError:
                pass
        
        # Apply time of day filter
        if time_of_day:
            time_list = [t.strip() for t in time_of_day.split(',')]
            time_conditions = []
            for time_val in time_list:
                try:
                    hour = int(time_val)
                    if 0 <= hour <= 23:
                        time_conditions.append(extract('hour', JournalEntry.date) == hour)
                except ValueError:
                    pass
            if time_conditions:
                query = query.filter(or_(*time_conditions))
        
        # Apply day of week filter
        if day_of_week:
            day_list = [d.strip() for d in day_of_week.split(',')]
            day_conditions = []
            for day_val in day_list:
                try:
                    day = int(day_val)
                    if 0 <= day <= 6:  # 0=Monday, 6=Sunday
                        day_conditions.append(extract('dow', JournalEntry.date) == day)
                except ValueError:
                    pass
            if day_conditions:
                query = query.filter(or_(*day_conditions))
        
        # Apply month filter
        if month:
            month_list = [m.strip() for m in month.split(',')]
            month_conditions = []
            for month_val in month_list:
                try:
                    month_int = int(month_val)
                    if 1 <= month_int <= 12:
                        month_conditions.append(extract('month', JournalEntry.date) == month_int)
                except ValueError:
                    pass
            if month_conditions:
                query = query.filter(or_(*month_conditions))
        
        # Apply year filter
        if year:
            year_list = [y.strip() for y in year.split(',')]
            year_conditions = []
            for year_val in year_list:
                try:
                    year_int = int(year_val)
                    if 2000 <= year_int <= 2100:  # Reasonable year range
                        year_conditions.append(extract('year', JournalEntry.date) == year_int)
                except ValueError:
                    pass
            if year_conditions:
                query = query.filter(or_(*year_conditions))
        
        # Get filtered entries
        entries = query.all()
        
        # Apply variables filter if provided (post-query filtering)
        if variables_param:
            try:
                variables_filter = json.loads(variables_param)
                if isinstance(variables_filter, dict) and variables_filter:
                    filtered_entries = []
                    for entry in entries:
                        matches_all = True
                        for var_name, var_values in variables_filter.items():
                            if not isinstance(var_values, list) or not var_values:
                                continue
                            
                            entry_vars = entry.variables or {}
                            if isinstance(entry_vars, dict):
                                entry_value = entry_vars.get(var_name)
                                if entry_value:
                                    if isinstance(entry_value, list):
                                        entry_values = [str(v).strip().lower() for v in entry_value if v]
                                    else:
                                        entry_values = [str(entry_value).strip().lower()]
                                else:
                                    extra_data = entry.extra_data or {}
                                    if isinstance(extra_data, dict):
                                        entry_value = extra_data.get(var_name)
                                        if entry_value:
                                            if isinstance(entry_value, list):
                                                entry_values = [str(v).strip().lower() for v in entry_value if v]
                                            else:
                                                entry_values = [str(entry_value).strip().lower()]
                                        else:
                                            entry_values = []
                                    else:
                                        entry_values = []
                            else:
                                entry_values = []
                            
                            filter_values = [str(v).strip().lower() for v in var_values if v]
                            if not any(ev in filter_values for ev in entry_values):
                                matches_all = False
                                break
                        
                        if matches_all:
                            filtered_entries.append(entry)
                    
                    entries = filtered_entries
            except (json.JSONDecodeError, TypeError):
                pass

        if not entries:
            return jsonify({
                "total_trades": 0,
                "total_pnl": 0.0,
                "win_rate": 0.0,
                "profit_factor": None,
                "avg_rr": 0.0,
                "max_drawdown": 0.0,
                "expectancy": 0.0,
                "kelly_percentage": 0.0,
                "sharpe_ratio": 0.0,
                "sortino_ratio": None,
                "recovery_factor": None,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "avg_pnl": 0.0,
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0,
                "buy_pnl": 0.0,
                "sell_pnl": 0.0,
                "win_loss": {"wins": 0, "losses": 0},
                "best_trade": {"symbol": None, "pnl": 0.0, "date": None, "rr": 0.0},
                "worst_trade": {"symbol": None, "pnl": 0.0, "date": None, "rr": 0.0},
                "equity_curve": [],
                "pnl_by_date": [],
                "gross_profit": 0.0,
                "gross_loss": 0.0,
                "top_symbols": [],
                "recent_trades": [],
                "best_day_of_week": {"day": None, "pnl": 0.0},
                "worst_day_of_week": {"day": None, "pnl": 0.0},
                "best_hour": {"hour": None, "pnl": 0.0},
                "worst_hour": {"hour": None, "pnl": 0.0},
                "max_drawdown_percent": 0.0,
                "symbols": [],
                "strategies": [],
                "setups": [],
                "trades": []
            }), 200
        total_trades = len(entries)
        total_pnl = sum(e.pnl for e in entries)

        # Calculate wins, losses, and break-even trades
        wins = [e for e in entries if e.pnl > 0]
        losses = [e for e in entries if e.pnl < 0]
        break_even = [e for e in entries if e.pnl == 0]
        
        win_count = len(wins)
        loss_count = len(losses)
        break_even_count = len(break_even)
        
        # Calculate win rate as (winning trades / (total trades - break even trades))
        total_trades_without_break_even = total_trades - break_even_count
        win_rate = (win_count / total_trades_without_break_even) * 100 if total_trades_without_break_even else 0.0

        gross_profit = sum(e.pnl for e in wins)
        gross_loss = abs(sum(e.pnl for e in losses))
        pf_raw = (gross_profit / gross_loss) if gross_loss != 0 else (
            float('inf') if gross_profit > 0 else 0.0
        )
        profit_factor = None if not math.isfinite(pf_raw) else round(pf_raw, 2)

        avg_rr_raw = sum(e.rr for e in entries) / total_trades if total_trades else 0.0
        avg_rr = round(avg_rr_raw, 2)

        # Build equity curve
        equity = 0.0
        equity_curve = []
        for e in entries:
            equity += e.pnl
            trade_dt = e.date or e.created_at
            equity_curve.append({
                "date": trade_dt.strftime("%Y-%m-%d"),
                "cumulative_pnl": round(equity, 2)
            })

        # Compute max drawdown (absolute)
        peak = equity_curve[0]["cumulative_pnl"]
        max_dd = 0.0
        for point in equity_curve:
            if point["cumulative_pnl"] > peak:
                peak = point["cumulative_pnl"]
            drawdown = peak - point["cumulative_pnl"]
            if drawdown > max_dd:
                max_dd = drawdown
        max_drawdown = round(max_dd, 2)

        # PnL by date
        pnl_by_date_dict = {}
        for e in entries:
            date_key = (e.date or e.created_at).strftime("%Y-%m-%d")
            pnl_by_date_dict.setdefault(date_key, 0.0)
            pnl_by_date_dict[date_key] += e.pnl
        pnl_by_date = [[date, pnl] for date, pnl in pnl_by_date_dict.items()]

        # Expectancy, Kelly, Sharpe, Sortino, Recovery
        avg_win_val = (sum(e.pnl for e in wins) / win_count) if win_count else 0.0
        avg_loss_val = (abs(sum(e.pnl for e in losses)) / loss_count) if loss_count else 0.0

        expectancy_raw = (
            (avg_win_val * (win_rate / 100)) -
            (avg_loss_val * (loss_count / total_trades))
        ) if total_trades else 0.0
        expectancy = round(expectancy_raw, 2)

        w = win_rate / 100.0
        r_ratio = (avg_win_val / avg_loss_val) if avg_loss_val != 0 else float('inf')
        kelly_raw = (w - ((1 - w) / r_ratio)) * 100 if (avg_loss_val and win_count) else 0.0
        kelly_percentage = None if not math.isfinite(kelly_raw) else round(kelly_raw, 2)

        pl_values = [e.pnl for e in entries]
        mean_pnl = sum(pl_values) / total_trades

        # Calculate Sharpe Ratio using daily returns based on previous equity with user initial balance
        # Group trades by date
        trades_by_date = {}
        for entry in entries:
            trade_date = entry.date.strftime('%Y-%m-%d') if entry.date else entry.created_at.strftime('%Y-%m-%d')
            if trade_date not in trades_by_date:
                trades_by_date[trade_date] = []
            trades_by_date[trade_date].append(entry)
        
        # Sort dates chronologically
        sorted_dates = sorted(trades_by_date.keys())
        
        # Calculate daily returns using previous equity, starting from user's initial balance
        daily_returns = []
        try:
            user_for_balance = User.query.get(user_id)
            user_initial_balance = float(user_for_balance.initial_balance) if (user_for_balance and getattr(user_for_balance, 'initial_balance', 0)) else 0.0
        except Exception:
            user_initial_balance = 0.0
        
        if user_initial_balance > 0:
            previous_equity = user_initial_balance
            for date_key in sorted_dates:
                daily_pnl = sum(entry.pnl for entry in trades_by_date[date_key] if entry.pnl is not None)
                daily_return = (daily_pnl / previous_equity) if previous_equity != 0 else 0.0
                daily_returns.append(daily_return)
                previous_equity += daily_pnl
        else:
            # No valid initial balance → cannot compute meaningful Sharpe
            daily_returns = []
        
        # Calculate Sharpe Ratio (annualized with 252 trading days)
        if len(daily_returns) >= 2:  # Need at least 2 points for stddev
            mean_return = sum(daily_returns) / len(daily_returns)
            stddev = (sum((x - mean_return) ** 2 for x in daily_returns) / len(daily_returns)) ** 0.5
            sharpe_ratio = round((mean_return / stddev * (252 ** 0.5)) if stddev != 0 else 0.0, 2)
        else:
            sharpe_ratio = 0.0

        # Sortino Ratio: downside deviation uses only negative returns
        # Use daily returns for proper calculation
        if len(daily_returns) >= 2:
            mean_return = sum(daily_returns) / len(daily_returns)
            # Risk-free rate (assuming 2% annual, converted to daily)
            risk_free_rate_daily = 0.02 / 252
            
            # Calculate downside deviation (only negative returns)
            downside_returns = [r for r in daily_returns if r < 0]
            if len(downside_returns) > 0:
                downside_variance = sum(r ** 2 for r in downside_returns) / len(downside_returns)
                downside_std = math.sqrt(downside_variance)
                
                # Use a minimum threshold to avoid division by zero when all trades have same risk
                min_downside_std = 0.05  # 5% minimum daily downside deviation (more realistic for trading)
                effective_downside_std = max(downside_std, min_downside_std)
                
                # Annualize the ratio
                sortino_raw = ((mean_return - risk_free_rate_daily) / effective_downside_std) * math.sqrt(252)
                
                # Cap the Sortino ratio to realistic values (max 5)
                sortino_ratio = min(round(sortino_raw, 2), 5.0) if math.isfinite(sortino_raw) else 0.0
            else:
                # No downside risk - perfect scenario
                sortino_ratio = 5.0 if mean_return > risk_free_rate_daily else 0.0  # Cap at 5 instead of infinity
        else:
            sortino_ratio = 0.0

        rec_raw = (total_pnl / max_dd) if max_dd != 0 else (
            float('inf') if total_pnl > 0 else 0.0
        )
        recovery_factor = None if not math.isfinite(rec_raw) else round(rec_raw, 2)

        # Consecutive wins/losses
        consec_wins = consec_losses = max_consec_wins = max_consec_losses = 0
        for e in entries:
            if e.pnl > 0:
                consec_wins += 1
                consec_losses = 0
            else:
                consec_losses += 1
                consec_wins = 0
            max_consec_wins = max(max_consec_wins, consec_wins)
            max_consec_losses = max(max_consec_losses, consec_losses)

        buy_pnl = sum(e.pnl for e in entries if e.direction.lower() == 'long')
        sell_pnl = sum(e.pnl for e in entries if e.direction.lower() == 'short')

        # Best / Worst trades
        best_trade_obj = max(entries, key=lambda x: x.pnl)
        worst_trade_obj = min(entries, key=lambda x: x.pnl)
        best_trade = {
            "symbol": best_trade_obj.symbol,
            "pnl": best_trade_obj.pnl,
            "date": best_trade_obj.created_at.strftime("%Y-%m-%d"),
            "rr": best_trade_obj.rr
        }
        worst_trade = {
            "symbol": worst_trade_obj.symbol,
            "pnl": worst_trade_obj.pnl,
            "date": worst_trade_obj.created_at.strftime("%Y-%m-%d"),
            "rr": worst_trade_obj.rr
        }

        # Top-performing symbols
        symbol_totals = {}
        for e in entries:
            symbol_totals.setdefault(e.symbol, {"pnl": 0.0, "trades": 0, "wins": 0})
            symbol_totals[e.symbol]["pnl"] += e.pnl
            symbol_totals[e.symbol]["trades"] += 1
            if e.pnl > 0:
                symbol_totals[e.symbol]["wins"] += 1

        top_symbols = sorted(
            symbol_totals.items(),
            key=lambda kv: kv[1]["pnl"],
            reverse=True
        )
        top_symbols_clean = [[sym, data] for sym, data in top_symbols[:6]]

        # Recent trades
        # Recent trades
        recent_trades_objs = sorted(entries, key=lambda x: (x.date or x.created_at), reverse=True)[:5]
        recent_trades = []
        for e in recent_trades_objs:
            recent_trades.append({
                "symbol": e.symbol,
                "direction": "Long" if e.direction.lower() == "long" else "Short",
                "date": (e.date or e.created_at).strftime("%Y-%m-%d"),
                "pnl": e.pnl,
                "rr": e.rr,
                "strategy": e.strategy.name if e.strategy else "N/A",
                "setup": e.notes or "",
                "entry_screenshot": e.entry_screenshot,
                "exit_screenshot": e.exit_screenshot,
                "entry_price": e.entry_price,
                "exit_price": e.exit_price,
                "quantity": e.quantity,
                "notes": e.notes
            })

        # ===== ADDITIONAL TIME-BASED METRICS =====

        # 1) Day-of-week P&L totals (0=Monday, ..., 6=Sunday)
        day_of_week_map = {i: 0.0 for i in range(7)}
        # 2) Hourly P&L totals (0..23)
        hour_map = {h: 0.0 for h in range(24)}

        for e in entries:
            dt = e.created_at
            dow = dt.weekday()  # Monday=0
            day_of_week_map[dow] += e.pnl
            hour_map[dt.hour] += e.pnl

        # Best/Worst day of week
        best_dow_index = max(day_of_week_map, key=lambda k: day_of_week_map[k])
        worst_dow_index = min(day_of_week_map, key=lambda k: day_of_week_map[k])
        dow_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        best_day_of_week = {
            "day": dow_labels[best_dow_index],
            "pnl": round(day_of_week_map[best_dow_index], 2)
        }
        worst_day_of_week = {
            "day": dow_labels[worst_dow_index],
            "pnl": round(day_of_week_map[worst_dow_index], 2)
        }

        # Best/Worst hour
        best_hour = max(hour_map, key=lambda h: hour_map[h])
        worst_hour = min(hour_map, key=lambda h: hour_map[h])
        best_hour_obj = {
            "hour": best_hour,
            "pnl": round(hour_map[best_hour], 2)
        }
        worst_hour_obj = {
            "hour": worst_hour,
            "pnl": round(hour_map[worst_hour], 2)
        }

        # Max drawdown percent
        peak_equity = max([pt["cumulative_pnl"] for pt in equity_curve] + [1.0])
        max_drawdown_percent = round((max_dd / peak_equity) * 100, 2) if peak_equity else 0.0

        # Extract unique symbols, strategies, and setups for filter options
        symbols = sorted(list(set([e.symbol for e in entries if e.symbol])))
        strategies = sorted(list(set([e.strategy for e in entries if e.strategy])))
        setups = sorted(list(set([e.setup for e in entries if e.setup])))

        # Get initial balance from user's profile or default to 0
        initial_balance = 0.0
        try:
            user = User.query.get(user_id)
            if user and hasattr(user, 'initial_balance') and user.initial_balance:
                initial_balance = float(user.initial_balance)
        except Exception as e:
            print(f"Error getting initial balance: {e}")
            initial_balance = 0.0

        return jsonify({
            "total_trades": total_trades,
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": round((total_pnl / initial_balance * 100), 2) if initial_balance > 0 else 0.0,
            "initial_balance": round(initial_balance, 2),
            "current_balance": round(initial_balance + total_pnl, 2),
            "win_rate": round(win_rate, 2),
            "profit_factor": profit_factor,
            "avg_rr": avg_rr,
            "max_drawdown": max_drawdown,
            "expectancy": expectancy,
            "kelly_percentage": kelly_percentage,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": None if not math.isfinite(sortino_ratio) else sortino_ratio,
            "recovery_factor": recovery_factor,
            "avg_win": round(avg_win_val, 2),
            "avg_loss": round(avg_loss_val, 2),
            "avg_pnl": round(mean_pnl, 2),
            "max_consecutive_wins": max_consec_wins,
            "max_consecutive_losses": max_consec_losses,
            "buy_pnl": round(buy_pnl, 2),
            "sell_pnl": round(sell_pnl, 2),
            "win_loss": {"wins": win_count, "losses": loss_count},
            "best_trade": best_trade,
            "worst_trade": worst_trade,
            "equity_curve": equity_curve,
            "pnl_by_date": pnl_by_date,
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "top_symbols": top_symbols_clean,
            "recent_trades": recent_trades,
            "best_day_of_week": best_day_of_week,
            "worst_day_of_week": worst_day_of_week,
            "best_hour": best_hour_obj,
            "worst_hour": worst_hour_obj,
            "max_drawdown_percent": max_drawdown_percent,
            "symbols": symbols,
            "strategies": strategies,
            "setups": setups,
            "trades": [
                {
                    "id": e.id,
                    "symbol": e.symbol,
                    "direction": e.direction,
                    "pnl": e.pnl,
                    "rr": e.rr,
                    "entry_price": e.entry_price,
                    "exit_price": e.exit_price,
                    "high_price": e.high_price,
                    "low_price": e.low_price,
                    "stop_loss": e.stop_loss,
                    "take_profit": e.take_profit,
                    "open_time": e.open_time.isoformat() if e.open_time else None,
                    "close_time": e.close_time.isoformat() if e.close_time else None,
                    "quantity": e.quantity,
                    "instrument_type": e.instrument_type,
                    "contract_size": e.contract_size,
                    "risk_amount": e.risk_amount,
                    "strategy": e.strategy,
                    "setup": e.setup,
                    "notes": e.notes,
                    "date": (e.date or e.entry_date or e.created_at).strftime("%Y-%m-%d")
                }
                for e in entries
            ]
        }), 200

    except Exception as e:
        print(" stats error:", e)
        return jsonify({"error": str(e)}), 500


@journal_bp.route('/stats/all', methods=['GET'])
@jwt_required()
def get_all_stats():
    user_id = get_jwt_identity()
    # --- FILTERS (copied from variables_analysis) ---
    from datetime import datetime, timedelta
    import json
    query = JournalEntry.query.filter_by(user_id=user_id).order_by(JournalEntry.date.asc())

    # Date range
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    if from_date:
        try:
            from_date_dt = datetime.strptime(from_date, '%Y-%m-%d')
            query = query.filter(JournalEntry.date >= from_date_dt)
        except ValueError:
            return jsonify({'error': 'Invalid from_date format. Use YYYY-MM-DD'}), 400
    if to_date:
        try:
            to_date_dt = datetime.strptime(to_date, '%Y-%m-%d')
            query = query.filter(JournalEntry.date <= to_date_dt)
        except ValueError:
            return jsonify({'error': 'Invalid to_date format. Use YYYY-MM-DD'}), 400

    # Symbol
    symbols = request.args.get('symbols')
    if symbols:
        symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
        if symbol_list:
            query = query.filter(JournalEntry.symbol.in_(symbol_list))

    # Direction
    directions = request.args.get('directions')
    if directions:
        direction_list = [d.strip() for d in directions.split(',') if d.strip()]
        if direction_list:
            query = query.filter(JournalEntry.direction.in_(direction_list))

    # Strategy
    strategies = request.args.get('strategies')
    if strategies:
        strategy_list = [s.strip() for s in strategies.split(',') if s.strip()]
        if strategy_list:
            query = query.filter(JournalEntry.strategy.in_(strategy_list))

    # Setup
    setups = request.args.get('setups')
    if setups:
        setup_list = [s.strip() for s in setups.split(',') if s.strip()]
        if setup_list:
            query = query.filter(JournalEntry.setup.in_(setup_list))

    # P&L range
    min_pnl = request.args.get('min_pnl')
    if min_pnl:
        try:
            min_pnl_val = float(min_pnl)
            query = query.filter(JournalEntry.pnl >= min_pnl_val)
        except ValueError:
            pass
    max_pnl = request.args.get('max_pnl')
    if max_pnl:
        try:
            max_pnl_val = float(max_pnl)
            query = query.filter(JournalEntry.pnl <= max_pnl_val)
        except ValueError:
            pass

    # R:R range
    min_rr = request.args.get('min_rr')
    if min_rr:
        try:
            min_rr_val = float(min_rr)
            query = query.filter(JournalEntry.rr >= min_rr_val)
        except ValueError:
            pass
    max_rr = request.args.get('max_rr')
    if max_rr:
        try:
            max_rr_val = float(max_rr)
            query = query.filter(JournalEntry.rr <= max_rr_val)
        except ValueError:
            pass

    # Import batch
    batch_ids = request.args.get('batch_ids')
    if batch_ids:
        try:
            batch_id_list = [int(b.strip()) for b in batch_ids.split(',') if b.strip()]
            if batch_id_list:
                query = query.filter(JournalEntry.import_batch_id.in_(batch_id_list))
        except ValueError:
            pass

    entries = query.all()

    # Apply variables filter if provided
    variables_param = request.args.get('variables')
    if variables_param:
        try:
            variables_filter = json.loads(variables_param)
            if isinstance(variables_filter, dict) and variables_filter:
                entries = [trade for trade in entries if apply_variables_filter(trade, variables_filter)]
        except (json.JSONDecodeError, TypeError):
            # Ignore malformed variables filter
            pass

    trades = entries
    if not trades:
        return jsonify({}), 200

    pnl_values = np.array([trade.pnl for trade in trades if trade.pnl is not None])
    win_trades = [t.pnl for t in trades if t.pnl is not None and t.pnl > 0]
    loss_trades = [t.pnl for t in trades if t.pnl is not None and t.pnl < 0]

    # Basic stats
    total_trades = len(trades)
    total_pnl = sum(pnl_values)
    avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
    win_rate = len(win_trades) / total_trades * 100 if total_trades > 0 else 0
    avg_win = sum(win_trades) / len(win_trades) if win_trades else 0
    avg_loss = sum(loss_trades) / len(loss_trades) if loss_trades else 0

    # Risk-reward
    rr_values = [t.rr for t in trades if t.rr is not None]
    avg_rr = sum(rr_values) / len(rr_values) if rr_values else 0

    # Best/Worst Trades
    best_trade = max(trades, key=lambda t: t.pnl, default=None)
    worst_trade = min(trades, key=lambda t: t.pnl, default=None)

    # Profitability
    gross_profit = sum(win_trades)
    gross_loss = sum(loss_trades)
    profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else 0
    expectancy = (win_rate / 100 * avg_win) + ((100 - win_rate) / 100 * avg_loss)

    # Max Drawdown
    equity_curve = np.cumsum(pnl_values)
    peak = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - peak)
    max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0
    max_drawdown_percent = 0
    if np.max(peak) > 0:
        max_drawdown_percent = (max_drawdown / np.max(peak)) * 100

    # Consecutive Wins/Losses
    max_consecutive_wins = 0
    max_consecutive_losses = 0
    current_wins = 0
    current_losses = 0
    for pnl in pnl_values:
        if pnl > 0:
            current_wins += 1
            current_losses = 0
        else:
            current_losses += 1
            current_wins = 0
        max_consecutive_wins = max(max_consecutive_wins, current_wins)
        max_consecutive_losses = max(max_consecutive_losses, current_losses)

    recovery_factor = total_pnl / abs(max_drawdown) if max_drawdown != 0 else 0

    # --- ADVANCED & EFFICIENCY METRICS (MAE, MFE, etc.) ---
    mae_list = []
    mfe_list = []
    winners_mae = []
    losers_mae = []
    winners_mfe = []
    losers_mfe = []
    
    # Debug counters
    skipped_trades = 0
    invalid_entry_price = 0
    processed_trades = 0
    
    for trade in trades:
        # Validate required fields
        if not all([trade.entry_price, trade.exit_price, trade.direction]):
            skipped_trades += 1
            continue
            
        try:
            entry = float(trade.entry_price)
            exit_price = float(trade.exit_price)
            
            # Skip trades with invalid entry price (0 or negative)
            if entry <= 0:
                invalid_entry_price += 1
                continue
                
            # Get high/low prices with fallbacks
            high_price = float(getattr(trade, 'high_price', exit_price) or exit_price)
            low_price = float(getattr(trade, 'low_price', exit_price) or exit_price)
            
            # Ensure high/low prices are valid
            if high_price <= 0 or low_price <= 0:
                high_price = max(entry, exit_price)
                low_price = min(entry, exit_price)
            
            is_long = trade.direction.upper() in ['LONG', 'BUY']
            
            # Calculate P&L percentage
            if is_long:
                pnl_pct = ((exit_price - entry) / entry) * 100
            else:
                pnl_pct = ((entry - exit_price) / entry) * 100
                
            # Calculate MAE/MFE with validation
            if is_long:
                max_price = max(high_price, exit_price, entry)
                min_price = min(low_price, exit_price, entry)
                mfe = ((max_price - entry) / entry) * 100
                mae = ((min_price - entry) / entry) * 100
            else:
                max_price = max(high_price, exit_price, entry)
                min_price = min(low_price, exit_price, entry)
                mfe = ((entry - min_price) / entry) * 100
                mae = ((entry - max_price) / entry) * 100
                
            # Validate calculated values
            if not (np.isnan(mae) or np.isnan(mfe) or np.isinf(mae) or np.isinf(mfe)):
                mae_list.append(abs(mae))
                mfe_list.append(mfe)
                processed_trades += 1
                
                if pnl_pct > 0:
                    winners_mae.append(abs(mae))
                    winners_mfe.append(mfe)
                else:
                    losers_mae.append(abs(mae))
                    losers_mfe.append(mfe)
                    
        except (ValueError, TypeError, ZeroDivisionError) as e:
            # Skip trades with calculation errors
            skipped_trades += 1
            continue
    
    # Calculate averages with validation
    avg_mae = sum(mae_list) / len(mae_list) if mae_list else 0
    avg_mfe = sum(mfe_list) / len(mfe_list) if mfe_list else 0
    avg_winning_mae = sum(winners_mae) / len(winners_mae) if winners_mae else 0
    avg_losing_mae = sum(losers_mae) / len(losers_mae) if losers_mae else 0
    avg_winning_mfe = sum(winners_mfe) / len(winners_mfe) if winners_mfe else 0
    avg_losing_mfe = sum(losers_mfe) / len(losers_mfe) if losers_mfe else 0
    
    # Debug logging
    print(f"Advanced Metrics Debug: Processed {processed_trades} trades, Skipped {skipped_trades}, Invalid entry price: {invalid_entry_price}")
    print(f"MAE/MFE Lists: mae_list={len(mae_list)}, mfe_list={len(mfe_list)}, winners_mae={len(winners_mae)}, losers_mae={len(losers_mae)}")

    # --- IMPROVED ADVANCED METRICS ---
    k_ratio = 0
    z_score = 0
    gpr = 0
    etd = 0
    
    try:
        # K-Ratio calculation
        equity_curve = np.cumsum([t.pnl for t in trades if t.pnl is not None])
        x = np.arange(len(equity_curve))
        
        if SCIPY_AVAILABLE and len(equity_curve) > 1:
            try:
                slope, intercept, r_value, p_value, std_err = linregress(x, equity_curve)
                k_ratio = slope / std_err if std_err != 0 and not np.isnan(std_err) else 0
            except:
                k_ratio = 0
        
        # Z-Score (streakiness) with validation
        results = [1 if t.pnl > 0 else 0 for t in trades if t.pnl is not None]
        if len(results) > 1:
            n1 = sum(results)
            n2 = len(results) - n1
            runs = 1 + sum(results[i] != results[i-1] for i in range(1, len(results)))
            expected_runs = ((2 * n1 * n2) / (n1 + n2)) + 1 if (n1 + n2) > 0 else 0
            variance_runs = (2 * n1 * n2 * (2 * n1 * n2 - n1 - n2)) / (((n1 + n2) ** 2) * (n1 + n2 - 1)) if (n1 + n2) > 1 else 0
            z_score = (runs - expected_runs) / np.sqrt(variance_runs) if variance_runs > 0 and not np.isnan(variance_runs) else 0
        
        # GPR (Gain-to-Pain Ratio) with validation
        gains = sum(t.pnl for t in trades if t.pnl and t.pnl > 0)
        pains = sum(abs(t.pnl) for t in trades if t.pnl and t.pnl < 0)
        gpr = gains / pains if pains > 0 and not np.isnan(pains) else 0
        
        # ETD (Efficiency to Drawdown) with validation
        net_profit = sum(t.pnl for t in trades if t.pnl is not None)
        if len(equity_curve) > 0:
            peak = np.maximum.accumulate(equity_curve)
            drawdown = equity_curve - peak
            max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0
            etd = net_profit / abs(max_drawdown) if max_drawdown != 0 and not np.isnan(max_drawdown) else 0
        else:
            etd = 0
            
    except Exception as e:
        print(f"Advanced Metrics calculation error: {e}")
        # Keep default values (0) if calculation fails

    # --- TIME & COST METRICS ---
    durations = []
    holding_times_per_unit = []
    for t in trades:
        if t.open_time and t.close_time:
            duration = (t.close_time - t.open_time).total_seconds()
            durations.append(duration)
            if t.quantity:
                holding_times_per_unit.append(duration / t.quantity)
    avg_trade_duration_seconds = sum(durations) / len(durations) if durations else 0
    avg_holding_time_per_unit = sum(holding_times_per_unit) / len(holding_times_per_unit) if holding_times_per_unit else 0

    # Time-based analysis
    pnl_by_day_of_week = {i: 0 for i in range(7)}
    pnl_by_hour = {i: 0 for i in range(24)}
    for trade in trades:
        if trade.date:
            pnl_by_day_of_week[trade.date.weekday()] += trade.pnl
            pnl_by_hour[trade.date.hour] += trade.pnl

    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    best_day_pnl = -float('inf')
    worst_day_pnl = float('inf')
    best_day = None
    worst_day = None
    for day_index, pnl in pnl_by_day_of_week.items():
        if pnl > best_day_pnl:
            best_day_pnl = pnl
            best_day = days[day_index]
        if pnl < worst_day_pnl:
            worst_day_pnl = pnl
            worst_day = days[day_index]

    best_hour_pnl = -float('inf')
    worst_hour_pnl = float('inf')
    best_hour = None
    worst_hour = None
    for hour, pnl in pnl_by_hour.items():
        if pnl > best_hour_pnl:
            best_hour_pnl = pnl
            best_hour = hour
        if pnl < worst_hour_pnl:
            worst_hour_pnl = pnl
            worst_hour = hour

    # Advanced Metrics (Sharpe, Sortino, Kelly)
    # Use normalized daily returns based on previous equity starting from initial balance
    # This aligns with the Sharpe/Sortino logic used elsewhere and on the Equity page
    # Group trades by date
    trades_by_date = {}
    for t in trades:
        trade_date = t.date.strftime('%Y-%m-%d') if t.date else t.created_at.strftime('%Y-%m-%d')
        trades_by_date.setdefault(trade_date, []).append(t)

    sorted_dates = sorted(trades_by_date.keys())

    # Determine initial balance: prefer query param if provided, else user's stored balance
    user_initial_balance = 0.0
    try:
        initial_balance_param = request.args.get('initial_balance')
        if initial_balance_param is not None and initial_balance_param != '':
            user_initial_balance = float(initial_balance_param)
        else:
            user_obj = User.query.get(user_id)
            if user_obj and getattr(user_obj, 'initial_balance', 0):
                user_initial_balance = float(user_obj.initial_balance)
    except Exception:
        user_initial_balance = 0.0

    daily_returns = []
    if user_initial_balance > 0 and sorted_dates:
        previous_equity = user_initial_balance
        for date_key in sorted_dates:
            daily_pnl = sum((tr.pnl or 0.0) for tr in trades_by_date[date_key])
            # Normalize by previous equity to get daily return
            daily_return = (daily_pnl / previous_equity) if previous_equity != 0 else 0.0
            daily_returns.append(daily_return)
            previous_equity += daily_pnl

    # Sharpe Ratio (annualized, 252 trading days)
    sharpe_ratio = 0.0
    if len(daily_returns) >= 2:
        mean_return = float(np.mean(daily_returns))
        std_return = float(np.std(daily_returns, ddof=0))
        sharpe_ratio = round(((mean_return / std_return) * np.sqrt(252)) if std_return != 0 else 0.0, 2)

    # Sortino Ratio using downside deviation from daily returns
    sortino_ratio = 0.0
    if len(daily_returns) >= 2:
        negative_returns = [r for r in daily_returns if r < 0]
        if len(negative_returns) > 0:
            downside_std = float(np.std(negative_returns, ddof=0))
            # Use a minimum threshold to avoid division by zero when all trades have same risk
            min_downside_std = 0.05  # 5% minimum daily downside deviation (more realistic for trading)
            effective_downside_std = max(downside_std, min_downside_std)

            # Risk-free rate (assuming 2% annual, converted to daily)
            risk_free_rate_daily = 0.02 / 252
            mean_return = float(np.mean(daily_returns))
            sortino_raw = ((mean_return - risk_free_rate_daily) / effective_downside_std) * np.sqrt(252)
            # Cap the Sortino ratio to realistic values (max 5)
            sortino_ratio = min(sortino_raw, 5.0) if np.isfinite(sortino_raw) else 0.0

    kelly_percentage = 0
    if avg_win > 0 and avg_loss < 0:
        W = win_rate / 100
        R = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        if R > 0:
            kelly_percentage = (W - (1 - W) / R) * 100

    stats = {
        'total_trades': total_trades,
        'total_pnl': total_pnl,
        'avg_pnl': avg_pnl,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'avg_rr': avg_rr,
        'best_trade': {'pnl': best_trade.pnl, 'symbol': best_trade.symbol, 'date': best_trade.date.strftime('%Y-%m-%d')} if best_trade else None,
        'worst_trade': {'pnl': worst_trade.pnl, 'symbol': worst_trade.symbol, 'date': worst_trade.date.strftime('%Y-%m-%d')} if worst_trade else None,
        'profit_factor': profit_factor,
        'expectancy': expectancy,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'kelly_percentage': kelly_percentage,
        'max_drawdown': max_drawdown,
        'max_drawdown_percent': max_drawdown_percent,
        'max_consecutive_wins': max_consecutive_wins,
        'max_consecutive_losses': max_consecutive_losses,
        'recovery_factor': recovery_factor,
        'best_day_of_week': {'day': best_day, 'pnl': best_day_pnl} if best_day else None,
        'worst_day_of_week': {'day': worst_day, 'pnl': worst_day_pnl} if worst_day else None,
        'best_hour': {'hour': best_hour, 'pnl': best_hour_pnl} if best_hour is not None else None,
        'worst_hour': {'hour': worst_hour, 'pnl': worst_hour_pnl} if worst_hour is not None else None,
        # --- ADVANCED & EFFICIENCY METRICS (MAE, MFE, etc.) ---
        'avg_mae': avg_mae,
        'avg_mfe': avg_mfe,
        'avg_winning_mae': avg_winning_mae,
        'avg_losing_mae': avg_losing_mae,
        'avg_winning_mfe': avg_winning_mfe,
        'avg_losing_mfe': avg_losing_mfe,
        # --- IMPROVED ADVANCED METRICS ---
        'k_ratio': k_ratio,
        'z_score': z_score,
        'gpr': gpr,
        'etd': etd,
        # --- TIME & COST METRICS ---
        'avg_trade_duration_seconds': avg_trade_duration_seconds,
        'avg_holding_time_per_unit': avg_holding_time_per_unit,
        'win_loss_ratio': len(win_trades) / len(loss_trades) if loss_trades else 0,
        'avg_commission': sum(t.commission for t in trades if t.commission) / len([t for t in trades if t.commission]) if any(t.commission for t in trades) else 0,
        'total_commission': sum(t.commission for t in trades if t.commission),
        'avg_slippage': sum(t.slippage for t in trades if t.slippage) / len([t for t in trades if t.slippage]) if any(t.slippage for t in trades) else 0,
        'total_slippage': sum(t.slippage for t in trades if t.slippage),
        }

    return jsonify(stats), 200


@journal_bp.route('/delete/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_entry(id):
    try:
        user_id_str = get_jwt_identity()
        user_id = int(user_id_str)

        entry = JournalEntry.query.filter_by(id=id, user_id=user_id).first()
        if entry is None:
            return jsonify({'error': 'Trade not found or not yours'}), 404

        db.session.delete(entry)
        db.session.commit()
        return jsonify({'message': 'Journal entry deleted'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@journal_bp.route('/export', methods=['GET'])
@jwt_required()
def export_entries():
    """
    Export all journal entries as an .xlsx file with ALL fields.
    Includes all trade data, variables, extra_data, and metadata.
    """
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        
        # Get the current user to check account type
        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        # Build base query - handle group accounts differently
        if current_user.account_type == 'group' and current_user.group_id:
            # Group account: export trades from all group members
            group_members = User.query.filter_by(
                group_id=current_user.group_id,
                account_type='individual'
            ).all()
            user_ids = [member.id for member in group_members]
            
            if user_ids:
                entries = JournalEntry.query.filter(
                    JournalEntry.user_id.in_(user_ids)
                ).order_by(JournalEntry.date.asc()).all()
            else:
                # No group members found, return empty list
                entries = []
        else:
            # Individual account: export only their own trades from active profile
            entries = JournalEntry.query.filter_by(
                user_id=user_id, 
                profile_id=profile_id
            ).order_by(JournalEntry.date.asc()).all()

        from journal_export import create_journal_xlsx_bytes

        print(f"Export: Processing {len(entries)} entries for user {user_id}")

        output = io.BytesIO()
        output.write(create_journal_xlsx_bytes(entries))
        output.seek(0)
        
        print(f"Export: Excel file created successfully, size: {len(output.getvalue())} bytes")

        return send_file(
            output,
            download_name='trading_journal_complete.xlsx',
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        print(" export_entries error:", e)
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Export failed: {str(e)}'}), 500


# ─── Excel-upload importer at /import/excel ───────────────────────────────────
@journal_bp.route('/import/excel', methods=['POST'])
@jwt_required()
def import_entries_excel():
    """
    Upload an Excel file under multipart/form-data field "file".
    Saves the file to disk, creates an ImportBatch with filepath,
    then reads trades out of it and inserts JournalEntry rows.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)

        # 1) Create a new ImportBatch record (with placeholder filepath for now)
        filename = file.filename
        batch = ImportBatch(
            user_id=user_id,
            profile_id=profile_id,
            filename=filename,
            imported_at=datetime.utcnow(),
            filepath=''  # Will update in a momentaa
        )
        db.session.add(batch)
        db.session.flush()  # so batch.id is populated

        # 2) Save the uploaded file to disk under uploads/
        #    We use batch.id to make filename unique
        saved_filename = f"import_{batch.id}_{filename}"
        save_path = os.path.join(UPLOAD_FOLDER, saved_filename)
        file.save(save_path)

        # 3) Update the batch with its filepath
        batch.filepath = save_path
        db.session.commit()   # commit so that filepath is stored

        # 4) Read that same Excel file via pandas
        df = pd.read_excel(save_path)
        
        # Debug: Print column names to see what's available
        print(f"🔍 Debug - Excel file: {filename}")
        print(f"🔍 Debug - Excel columns found: {list(df.columns)}")
        print(f"🔍 Debug - First few rows data:")
        for i, (_, row) in enumerate(df.head(3).iterrows()):
            print(f"  Row {i+1}: {dict(row)}")
        
        # Check if variables_json column exists
        if 'variables_json' in df.columns:
            print(f"🔍 Debug - variables_json column found!")
            print(f"🔍 Debug - variables_json sample values:")
            for i, value in enumerate(df['variables_json'].head(3)):
                print(f"  Row {i+1} variables_json: {value} (type: {type(value)})")
        else:
            print(f"🔍 Debug - NO variables_json column found!")
        
        imported_count = 0

        for _, row in df.iterrows():
            symbol      = row.get('symbol')
            direction   = row.get('direction')
            entry_price = row.get('entry_price')
            exit_price  = row.get('exit_price')
            pnl         = row.get('pnl')

            # Skip if required fields are NaN
            if pd.isna(symbol) or pd.isna(direction) or pd.isna(entry_price) or pd.isna(exit_price) or pd.isna(pnl):
                continue

            # Determine trade date (use provided date or now)
            trade_date = None
            if 'entry_datetime' in row and not pd.isna(row['entry_datetime']):
                trade_date = pd.to_datetime(row['entry_datetime'], errors='coerce')
            elif 'trade_date' in row and not pd.isna(row['trade_date']):
                trade_date = pd.to_datetime(row['trade_date'], errors='coerce')
            elif 'date' in row and not pd.isna(row['date']):
                trade_date = pd.to_datetime(row['date'], errors='coerce')
            elif 'created_at' in row and not pd.isna(row['created_at']):
                trade_date = pd.to_datetime(row['created_at'], errors='coerce')
            
            if not pd.isna(trade_date):
                trade_date = trade_date.to_pydatetime()
            else:
                trade_date = datetime.utcnow()

            # Parse datetime fields
            open_time = None
            close_time = None
            if 'entry_datetime' in row and not pd.isna(row['entry_datetime']):
                try:
                    open_time = pd.to_datetime(row['entry_datetime'], errors='coerce').to_pydatetime()
                except:
                    pass
            if 'exit_datetime' in row and not pd.isna(row['exit_datetime']):
                try:
                    close_time = pd.to_datetime(row['exit_datetime'], errors='coerce').to_pydatetime()
                except:
                    pass

            # Parse variables and extra_data
            variables = {}
            extra_data = {}
            
            # Handle strategy and setup from variables field
            if 'strategy' in row and not pd.isna(row['strategy']):
                strategy_value = str(row['strategy']).strip()
                if strategy_value:
                    variables['strategy'] = [strategy_value]  # Keep original case for Arabic text
            
            if 'setup' in row and not pd.isna(row['setup']):
                setup_value = str(row['setup']).strip()
                if setup_value:
                    variables['setup'] = [setup_value]  # Keep original case for Arabic text
            
            # Handle custom variables (var1-var10)
            for i in range(1, 11):
                var_key = f'var{i}'
                if var_key in row and not pd.isna(row[var_key]):
                    extra_data[var_key] = str(row[var_key]).strip()
            
            # Also check for common custom variable column names
            custom_var_columns = ['bias', 'entry', 'narrative', 'custom1', 'custom2', 'custom3', 'custom4', 'custom5']
            for col in custom_var_columns:
                if col in row and not pd.isna(row[col]):
                    value = str(row[col]).strip()
                    if value:  # Only add if not empty
                        extra_data[col] = value
            
            # Check for any other columns that might contain variables
            variable_columns = ['emotion', 'market_condition', 'timeframe', 'risk_level', 'confidence']
            for col in variable_columns:
                if col in row and not pd.isna(row[col]):
                    value = str(row[col]).strip()
                    if value:  # Only add if not empty
                        variables[col] = [value]  # Store as list format
            
            # Handle variables_json if present
            if 'variables_json' in row and not pd.isna(row['variables_json']):
                try:
                    variables_json_str = str(row['variables_json']).strip()
                    print(f"🔍 Debug - variables_json raw value: '{variables_json_str}'")
                    
                    # Try to parse the JSON
                    parsed_vars = json.loads(variables_json_str)
                    print(f"🔍 Debug - parsed variables: {parsed_vars}")
                    
                    if isinstance(parsed_vars, dict):
                        variables.update(parsed_vars)
                        print(f"🔍 Debug - variables after update: {variables}")
                    else:
                        print(f"🔍 Debug - parsed_vars is not a dict, type: {type(parsed_vars)}")
                except json.JSONDecodeError as e:
                    print(f"🔍 Debug - JSON decode error: {e}")
                    print(f"🔍 Debug - Problematic JSON string: '{variables_json_str}'")
                    
                    # Try to fix common JSON issues
                    try:
                        # Remove extra quotes that Excel might add
                        fixed_json = variables_json_str.strip('"').strip("'")
                        # Replace single quotes with double quotes
                        fixed_json = fixed_json.replace("'", '"')
                        # Try parsing again
                        parsed_vars = json.loads(fixed_json)
                        print(f"🔍 Debug - Fixed JSON parsed successfully: {parsed_vars}")
                        if isinstance(parsed_vars, dict):
                            variables.update(parsed_vars)
                            print(f"🔍 Debug - variables after fixed JSON update: {variables}")
                    except Exception as fix_error:
                        print(f"🔍 Debug - Could not fix JSON: {fix_error}")
                        
                except Exception as e:
                    print(f"🔍 Debug - Other error parsing variables_json: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Handle extra_data_json if present
            if 'extra_data_json' in row and not pd.isna(row['extra_data_json']):
                try:
                    parsed_extra = json.loads(str(row['extra_data_json']))
                    if isinstance(parsed_extra, dict):
                        extra_data.update(parsed_extra)
                except:
                    pass
            
            # Debug: Print variables and extra_data for first few entries
            if imported_count < 3:
                print(f"🔍 Debug - Entry {imported_count + 1}:")
                print(f"  variables: {variables}")
                print(f"  extra_data: {extra_data}")

            # Parse numeric fields with proper error handling
            def safe_float(value, default=None):
                if pd.isna(value) or value is None:
                    return default
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return default

            # Debug: Print what we're about to save
            if imported_count < 3:
                print(f"🔍 Debug - About to save entry {imported_count + 1}:")
                print(f"  variables: {variables}")
                print(f"  extra_data: {extra_data}")
                print(f"  variables type: {type(variables)}")
                print(f"  extra_data type: {type(extra_data)}")
                print(f"  variables_json raw: {row.get('variables_json', 'NOT_FOUND')}")
                print(f"  variables_json type: {type(row.get('variables_json', 'NOT_FOUND'))}")
            
            entry = JournalEntry(
                user_id=user_id,
                profile_id=profile_id,
                symbol=str(symbol).upper(),
                direction=str(direction).lower(),
                entry_price=float(entry_price),
                exit_price=float(exit_price),
                stop_loss=safe_float(row.get('stop_loss')),
                take_profit=safe_float(row.get('take_profit')),
                high_price=safe_float(row.get('high_price')),
                low_price=safe_float(row.get('low_price')),
                quantity=safe_float(row.get('quantity'), 1.0),
                contract_size=safe_float(row.get('contract_size')),
                instrument_type=str(row.get('instrument_type', 'crypto')),
                risk_amount=safe_float(row.get('risk_amount'), 1.0),
                pnl=float(pnl),
                rr=safe_float(row.get('rr'), 0.0),
                strategy=str(row.get('strategy', '')) if not pd.isna(row.get('strategy')) else None,
                setup=str(row.get('setup', '')) if not pd.isna(row.get('setup')) else None,
                notes=str(row.get('notes', '')) if not pd.isna(row.get('notes')) else None,
                variables=variables if variables else None,
                extra_data=extra_data if extra_data else None,
                commission=safe_float(row.get('commission')),
                slippage=safe_float(row.get('slippage')),
                open_time=open_time,
                close_time=close_time,
                duration_seconds=safe_float(row.get('duration_seconds')),
                duration_minutes=safe_float(row.get('duration_minutes')),
                duration_hours=safe_float(row.get('duration_hours')),
                duration_category=str(row.get('duration_category', '')) if not pd.isna(row.get('duration_category')) else None,
                entry_screenshot=str(row.get('entry_screenshot', '')) if not pd.isna(row.get('entry_screenshot')) else None,
                exit_screenshot=str(row.get('exit_screenshot', '')) if not pd.isna(row.get('exit_screenshot')) else None,
                date=trade_date,
                created_at=trade_date,
                updated_at=trade_date,
                import_batch_id=batch.id
            )
            db.session.add(entry)
            imported_count += 1

        db.session.commit()
        return jsonify({'message': 'Excel import successful', 'imported': imported_count}), 200

    except Exception as e:
        db.session.rollback()
        print(" import_entries_excel error:", e)
        return jsonify({'error': str(e)}), 500


@journal_bp.route('/import', methods=['POST'])
@jwt_required()
def import_trades_json():
    """
    Accepts a list of trades (JSON‐array).  Each trade must have at least
    'symbol', 'direction' and 'pnl'.  Instead of immediately inserting them,
    we first create an ImportBatch row so that it shows up in /import/history.
    """
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        data = request.get_json()
        trades = data.get('trades', [])
        if not isinstance(trades, list):
            return jsonify({'error': 'Expected a list of trades'}), 400

        # 1) Create a new ImportBatch record (no file‐upload here, so filepath is blank)
        batch = ImportBatch(
            user_id=user_id,
            profile_id=profile_id,
            filename=data.get('filename', f'manual_import_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}'),
            imported_at=datetime.utcnow(),
            filepath=''   # no actual file on disk for JSON imports
        )
        db.session.add(batch)
        db.session.flush()   # so batch.id gets populated

        inserted_count = 0
        # 2) Insert each JournalEntry with import_batch_id=batch.id
        for t in trades:
            # only insert if required fields exist
            if not all(k in t for k in ('symbol', 'direction', 'pnl')):
                continue
            
            # Debug: Print the first trade to see what fields are being sent
            if inserted_count == 0:
                print(f"DEBUG: First trade data: {t}")
                print(f"DEBUG: created_at field: {t.get('created_at')}")
                print(f"DEBUG: date field: {t.get('date')}")

            symbol    = t['symbol'].upper()
            direction = t['direction'].lower()
            pnl       = float(t['pnl'])
            rr        = float(t.get('rr', 0.0))
            notes     = t.get('notes', '')

            # Handle optional High and Low prices
            high_price = t.get('high_price')
            if high_price is not None:
                try:
                    high_price = float(high_price)
                except (ValueError, TypeError):
                    high_price = None
            
            low_price = t.get('low_price')
            if low_price is not None:
                try:
                    low_price = float(low_price)
                except (ValueError, TypeError):
                    low_price = None

            # Handle optional Take Profit and Stop Loss
            take_profit = t.get('take_profit')
            if take_profit is not None:
                try:
                    take_profit = float(take_profit)
                except (ValueError, TypeError):
                    take_profit = None

            stop_loss = t.get('stop_loss')
            if stop_loss is not None:
                try:
                    stop_loss = float(stop_loss)
                except (ValueError, TypeError):
                    stop_loss = None

            # Parse trade date and time if provided
            trade_date = None
            trade_time = None
            created_at = None
            
            # First, check if we have a timestamp field (ISO format with time)
            if 'timestamp' in t and t['timestamp']:
                try:
                    created_at = datetime.fromisoformat(str(t['timestamp']).replace('Z', '+00:00'))
                    trade_date = created_at.date()
                except (ValueError, TypeError):
                    pass
            
            # Also check for entry_datetime field from frontend (datetime-local format)
            if not created_at and 'entry_datetime' in t and t['entry_datetime']:
                try:
                    # Handle datetime-local format (YYYY-MM-DDTHH:MM)
                    entry_datetime_str = str(t['entry_datetime'])
                    created_at = datetime.fromisoformat(entry_datetime_str)
                    trade_date = created_at.date()
                    print(f"Parsed entry_datetime from frontend: {created_at}")
                except (ValueError, TypeError) as e:
                    print(f"Error parsing entry_datetime '{t['entry_datetime']}': {e}")
                    pass
            
            # Also check for created_at field from frontend
            if not created_at and 'created_at' in t and t['created_at']:
                try:
                    # Handle ISO format with 'Z' timezone indicator
                    created_at_str = str(t['created_at'])
                    if created_at_str.endswith('Z'):
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    else:
                        created_at = datetime.fromisoformat(created_at_str)
                    trade_date = created_at.date()
                    print(f"Parsed created_at from frontend: {created_at}")
                except (ValueError, TypeError) as e:
                    print(f"Error parsing created_at '{t['created_at']}': {e}")
                    pass
            
            # If no timestamp, try to parse date and time separately
            if not created_at:
                # Parse date
                if 'date' in t and t['date']:
                    date_str = str(t['date']).strip()
                    if date_str:  # Only try parsing if we have a non-empty string
                        try:
                            # First try ISO format
                            trade_date = datetime.fromisoformat(date_str).date()
                        except (ValueError, TypeError):
                            try:
                                # Try parsing as YYYY-MM-DD
                                trade_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                            except (ValueError, TypeError):
                                try:
                                    # Try parsing as MM/DD/YYYY
                                    trade_date = datetime.strptime(date_str, '%m/%d/%Y').date()
                                except (ValueError, TypeError):
                                    try:
                                        # Try parsing as DD/MM/YYYY
                                        trade_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                                    except (ValueError, TypeError):
                                        pass  # Keep None if all parsing fails
                
                # Parse time if available
                if 'time' in t and t['time']:
                    time_str = str(t['time']).strip()
                    if time_str:
                        try:
                            # Try parsing as HH:MM:SS or HH:MM
                            if ':' in time_str:
                                time_parts = time_str.split(':')
                                hours = int(time_parts[0])
                                minutes = int(time_parts[1]) if len(time_parts) > 1 else 0
                                seconds = int(time_parts[2]) if len(time_parts) > 2 else 0
                                trade_time = (hours, minutes, seconds)
                        except (ValueError, IndexError):
                            pass
            
            # If we have both date and time, combine them
            if trade_date and trade_time:
                try:
                    created_at = datetime.combine(
                        trade_date, 
                        datetime.min.time().replace(
                            hour=trade_time[0], 
                            minute=trade_time[1], 
                            second=trade_time[2] if len(trade_time) > 2 else 0
                        )
                    )
                except (ValueError, TypeError):
                    pass
            
            # If we still don't have a created_at, create a unique timestamp based on the trade index
            if not created_at:
                if trade_date:
                    created_at = datetime.combine(trade_date, datetime.utcnow().time())
                    print(f"Created created_at from trade_date: {created_at}")
                else:
                    # Create a unique timestamp based on the trade index to avoid all trades having the same date
                    base_time = datetime.utcnow()
                    # Add seconds based on the trade index to ensure uniqueness
                    created_at = base_time + timedelta(seconds=inserted_count)
                    trade_date = created_at.date()
                    print(f"Created unique timestamp for trade {inserted_count}: {created_at}")
            else:
                print(f"Using parsed created_at: {created_at}")

            # Extract variables from the trade data and normalize to lowercase
            variables = {}
            # Check for common variable fields
            variable_fields = ['setup', 'mistake', 'emotion', 'strategy', 'market_condition']
            for field in variable_fields:
                if field in t and t[field]:
                    # If it's a list, process each item
                    if isinstance(t[field], list):
                        # Filter out empty strings, strip whitespace, and convert to lowercase
                        variables[field] = [
                            str(item).lower().strip() 
                            for item in t[field] 
                            if item and str(item).strip()
                        ]
                    else:
                        value = str(t[field]).strip().lower()
                        if value:  # Only add non-empty values
                            variables[field] = [value]
            
            # Also check for any fields that start with 'var_' as potential variables
            for key, value in t.items():
                if key.startswith('var_') and value:
                    var_name = key[4:].lower()  # Remove 'var_' prefix and convert to lowercase
                    if isinstance(value, list):
                        # Process each item in the list
                        variables[var_name] = [
                            str(item).lower().strip() 
                            for item in value 
                            if item is not None and str(item).strip()
                        ]
                    else:
                        value = str(value).strip().lower()
                        if value:  # Only add non-empty values
                            variables[var_name] = [value]
                            
            # Process any additional variables in extra_data
            if 'extra_data' in t and isinstance(t['extra_data'], dict):
                for key, value in t['extra_data'].items():
                    if key not in variables:  # Don't overwrite existing variables
                        if isinstance(value, list):
                            variables[key.lower()] = [
                                str(item).lower().strip() 
                                for item in value 
                                if item is not None and str(item).strip()
                            ]
                        elif value is not None and str(value).strip():
                            variables[key.lower()] = [str(value).lower().strip()]
            
            # If no variables were found, set to None to avoid storing empty dict
            variables = variables if variables else None
            
            # Get entry and exit prices with proper defaults
            entry_price = float(t.get('entry_price', 0.0)) if t.get('entry_price') is not None else 0.0
            exit_price = float(t.get('exit_price', 0.0)) if t.get('exit_price') is not None else 0.0
            
            # Parse open_time and close_time if provided
            open_time = None
            close_time = None
            
            if 'open_time' in t and t['open_time']:
                try:
                    open_time = datetime.fromisoformat(str(t['open_time']).replace('Z', '+00:00'))
                    if open_time.tzinfo is None:
                        open_time = open_time.replace(tzinfo=timezone.utc)
                    else:
                        open_time = open_time.astimezone(timezone.utc)
                except (ValueError, TypeError):
                    pass
            
            if 'close_time' in t and t['close_time']:
                try:
                    close_time = datetime.fromisoformat(str(t['close_time']).replace('Z', '+00:00'))
                    if close_time.tzinfo is None:
                        close_time = close_time.replace(tzinfo=timezone.utc)
                    else:
                        close_time = close_time.astimezone(timezone.utc)
                except (ValueError, TypeError):
                    pass
            
            # Parse additional fields that might be in the trade data
            commission = None
            slippage = None
            if 'commission' in t and t['commission'] is not None:
                try:
                    commission = float(t['commission'])
                except (ValueError, TypeError):
                    commission = None
            
            if 'slippage' in t and t['slippage'] is not None:
                try:
                    slippage = float(t['slippage'])
                except (ValueError, TypeError):
                    slippage = None
            
            # Parse duration fields
            duration_seconds = None
            duration_minutes = None
            duration_hours = None
            duration_category = None
            
            if 'duration_seconds' in t and t['duration_seconds'] is not None:
                try:
                    duration_seconds = int(t['duration_seconds'])
                except (ValueError, TypeError):
                    duration_seconds = None
            
            if 'duration_minutes' in t and t['duration_minutes'] is not None:
                try:
                    duration_minutes = int(t['duration_minutes'])
                except (ValueError, TypeError):
                    duration_minutes = None
            
            if 'duration_hours' in t and t['duration_hours'] is not None:
                try:
                    duration_hours = float(t['duration_hours'])
                except (ValueError, TypeError):
                    duration_hours = None
            
            if 'duration_category' in t and t['duration_category']:
                duration_category = str(t['duration_category'])
            
            # Parse screenshot fields
            entry_screenshot = None
            exit_screenshot = None
            if 'entry_screenshot' in t and t['entry_screenshot']:
                entry_screenshot = str(t['entry_screenshot'])
            if 'exit_screenshot' in t and t['exit_screenshot']:
                exit_screenshot = str(t['exit_screenshot'])
            
            # Handle strategy and setup fields
            strategy = None
            setup = None
            if 'strategy' in t and t['strategy']:
                strategy = str(t['strategy'])
            if 'setup' in t and t['setup']:
                setup = str(t['setup'])
            
            entry = JournalEntry(
                user_id=user_id,
                profile_id=profile_id,
                symbol=str(symbol).upper(),
                direction=str(direction).lower(),
                entry_price=entry_price,
                exit_price=exit_price,
                high_price=high_price,
                low_price=low_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                quantity=float(t.get('quantity', 1.0)),
                contract_size=float(t['contract_size']) if t.get('contract_size') is not None else None,
                instrument_type=t.get('instrument_type', 'crypto'),
                risk_amount=float(t.get('risk_amount', 0.0)) if t.get('risk_amount') is not None else 0.0,
                pnl=pnl,
                rr=rr,
                strategy=strategy,
                setup=setup,
                notes=notes,
                variables=variables,  # Save the extracted variables
                extra_data=t.get('extra_data', {}),
                commission=commission,
                slippage=slippage,
                open_time=open_time,  # Add open_time field
                close_time=close_time,  # Add close_time field
                duration_seconds=duration_seconds,
                duration_minutes=duration_minutes,
                duration_hours=duration_hours,
                duration_category=duration_category,
                entry_screenshot=entry_screenshot,
                exit_screenshot=exit_screenshot,
                date=created_at,  # Use the full datetime instead of just the date
                created_at=created_at,  # Use the parsed timestamp
                updated_at=created_at,  # Use parsed timestamp for update as well
                import_batch_id=batch.id
            )
            db.session.add(entry)
            inserted_count += 1

        # 3) Update the batch's trade_count before commit
        batch.trade_count = inserted_count

        db.session.commit()
        return jsonify({
            'message': f'Imported {inserted_count} trades',
            'inserted_count': inserted_count,
            'batch_id': batch.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@journal_bp.route('/market/benchmark', methods=['GET'])
@jwt_required(optional=True)
def market_benchmark():
    """Return daily closing prices for a benchmark symbol between start and end (YYYY-MM-DD)."""
    symbol = request.args.get('symbol', 'SPY').upper()
    start = request.args.get('start')
    end = request.args.get('end')
    if not start or not end:
        return jsonify({'error': 'start and end query parameters required (YYYY-MM-DD)'}), 400
    try:
        start_dt = datetime.strptime(start, '%Y-%m-%d')
        end_dt = datetime.strptime(end, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format, expected YYYY-MM-DD'}), 400
    try:
        data = yf.download(symbol, start=start_dt, end=end_dt, progress=False)
        close_series = data['Adj Close'] if 'Adj Close' in data else data['Close']
        result = [{'date': idx.strftime('%Y-%m-%d'), 'price': round(val, 2)} for idx, val in close_series.items() if not pd.isna(val)]
        return jsonify({'symbol': symbol, 'prices': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@journal_bp.route('/import/history', methods=['GET'])
@jwt_required()
def import_history():
    """
    Return list of past import batches for the current user.
    For group accounts, returns import history from all group members.
    For individual accounts, returns their own import history.
    """
    try:
        user_id_str = get_jwt_identity()
        user_id = int(user_id_str)
        
        # Get the current user to check account type
        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        # Determine which users' import batches to show
        if current_user.account_type == 'group' and current_user.group_id:
            # Group account: show import history from all group members
            group_members = User.query.filter_by(
                group_id=current_user.group_id,
                account_type='individual'
            ).all()
            user_ids = [member.id for member in group_members]
            
            if user_ids:
                batches = (
                    ImportBatch.query
                    .filter(ImportBatch.user_id.in_(user_ids))
                    .order_by(ImportBatch.imported_at.desc())
                    .all()
                )
            else:
                batches = []
        else:
            # Individual account: show only their own import history
            batches = (
                ImportBatch.query
                .filter_by(user_id=user_id)
                .order_by(ImportBatch.imported_at.desc())
                .all()
            )

        result = []
        for b in batches:
            trade_count = JournalEntry.query.filter_by(import_batch_id=b.id).count()
            # Construct a download URL (front end can hit this)
            download_url = f"/api/journal/import/file/{b.id}"
            
            # For group accounts, include the student name who imported
            imported_by = ""
            if current_user.account_type == 'group':
                batch_user = User.query.get(b.user_id)
                if batch_user:
                    imported_by = batch_user.full_name or batch_user.email

            result.append({
                'id': b.id,
                'filename': b.filename,
                'imported_at': b.imported_at.isoformat(),
                'trade_count': trade_count,
                'download_url': download_url,
                'imported_by': imported_by  # Only populated for group accounts
            })

        return jsonify(result), 200

    except Exception as e:
        print(" import_history error:", e)
        return jsonify({'error': str(e)}), 500

@journal_bp.route('/import/file/<int:batch_id>', methods=['GET'])
@jwt_required()
def download_imported_file(batch_id):
    """
    Send back the originally‐uploaded Excel file for a given import batch.
    """
    try:
        user_id_str = get_jwt_identity()
        user_id = int(user_id_str)

        batch = ImportBatch.query.filter_by(id=batch_id, user_id=user_id).first_or_404()
        if not batch.filepath or not os.path.isfile(batch.filepath):
            return jsonify({'error': 'File not found on server'}), 404

        # Use send_file with as_attachment=True so the browser downloads it
        return send_file(
            batch.filepath,
            as_attachment=True,
            download_name=batch.filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        print(" download_imported_file error:", e)
        return jsonify({'error': str(e)}), 500


@journal_bp.route('/import/<int:batch_id>', methods=['DELETE'])
@jwt_required()
def delete_import_batch(batch_id):
    """
    Delete a specific import batch (and its file + trades).
    """
    try:
        user_id_str = get_jwt_identity()
        user_id = int(user_id_str)

        batch = ImportBatch.query.filter_by(id=batch_id, user_id=user_id).first_or_404()

        # 1) Delete the file from disk (if it still exists)
        if batch.filepath and os.path.isfile(batch.filepath):
            os.remove(batch.filepath)

        # 2) Deleting the batch cascades to JournalEntry via relationship
        db.session.delete(batch)
        db.session.commit()
        return jsonify({'message': 'Import batch, its file, and trades deleted'}), 200

    except Exception as e:
        db.session.rollback()
        print(" delete_import_batch error:", e)
        return jsonify({'error': str(e)}), 500


@journal_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_entry(id):
    try:
        data = request.get_json()
        entry = JournalEntry.query.get_or_404(id)

        entry.symbol = data.get('symbol', entry.symbol)
        entry.direction = data.get('direction', entry.direction)
        entry.entry_price = data.get('entry_price', entry.entry_price)
        entry.exit_price = data.get('exit_price', entry.exit_price)
        if 'quantity' in data:
            entry.quantity = float(data['quantity']) if data['quantity'] is not None and data['quantity'] != '' else 1.0
        if 'instrument_type' in data:
            entry.instrument_type = data['instrument_type'] if data['instrument_type'] is not None else 'crypto'
        if 'stop_loss' in data:
            entry.stop_loss = float(data['stop_loss']) if data['stop_loss'] is not None else None
        if 'take_profit' in data:
            entry.take_profit = float(data['take_profit']) if data['take_profit'] is not None else None
        if 'high_price' in data:
            entry.high_price = float(data['high_price']) if data['high_price'] is not None else None
        if 'low_price' in data:
            entry.low_price = float(data['low_price']) if data['low_price'] is not None else None
        entry.pnl = data.get('pnl', entry.pnl)
        entry.rr = data.get('rr', entry.rr)
        entry.notes = data.get('notes', entry.notes)

        if 'entry_datetime' in data and data['entry_datetime']:
            try:
                # The frontend sends a local datetime string (e.g., "YYYY-MM-DDTHH:MM")
                entry.date = datetime.fromisoformat(data['entry_datetime'])
            except (ValueError, TypeError) as e:
                print(f"Error parsing entry_datetime '{data['entry_datetime']}' on update: {e}")
                # Keep original if format is invalid
                pass
        
        # Handle new fields
        if 'commission' in data:
            entry.commission = float(data['commission']) if data['commission'] is not None else None
        if 'slippage' in data:
            entry.slippage = float(data['slippage']) if data['slippage'] is not None else None
        if 'open_time' in data:
            if data['open_time']:
                try:
                    open_time = datetime.fromisoformat(data['open_time'].replace('Z', '+00:00'))
                    if open_time.tzinfo is None:
                        open_time = open_time.replace(tzinfo=timezone.utc)
                    else:
                        open_time = open_time.astimezone(timezone.utc)
                    entry.open_time = open_time
                except (ValueError, TypeError):
                    entry.open_time = None
            else:
                entry.open_time = None
        if 'close_time' in data:
            if data['close_time']:
                try:
                    close_time = datetime.fromisoformat(data['close_time'].replace('Z', '+00:00'))
                    if close_time.tzinfo is None:
                        close_time = close_time.replace(tzinfo=timezone.utc)
                    else:
                        close_time = close_time.astimezone(timezone.utc)
                    entry.close_time = close_time
                except (ValueError, TypeError):
                    entry.close_time = None
            else:
                entry.close_time = None

        if 'extra_data' in data:
            entry.extra_data = data['extra_data']
        if 'variables' in data:  
            entry.variables = data['variables']
        if 'entry_screenshot' in data:
            entry.entry_screenshot = data['entry_screenshot']
        if 'exit_screenshot' in data:
            entry.exit_screenshot = data['exit_screenshot']

        db.session.commit()
        return jsonify({'message': 'Journal entry updated'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@journal_bp.route('/strategy-analysis', methods=['GET'])
@jwt_required()
def strategy_analysis():
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        entries = build_group_aware_query(user_id, profile_id).all()

        strategy_map = {}

        for entry in entries:
            strategy = entry.strategy or 'Unspecified'
            stats = strategy_map.setdefault(strategy, {
                'trades': 0,
                'wins': 0,
                'total_rr': 0.0,
                'total_pnl': 0.0
            })

            if entry.pnl == 0:
                continue  # Skip break-even trades
                
            stats['trades'] += 1
            stats['total_rr'] += entry.rr or 0.0
            stats['total_pnl'] += entry.pnl or 0.0
            if entry.pnl > 0:
                stats['wins'] += 1

        result = []
        for strategy, data in strategy_map.items():
            total = data['trades']
            win_rate = (data['wins'] / total * 100) if total else 0.0
            avg_rr = (data['total_rr'] / total) if total else 0.0
            result.append({
                'strategy': strategy,
                'trades': total,
                'win_rate': round(win_rate, 1),
                'avg_rr': round(avg_rr, 2),
                'pnl': round(data['total_pnl'], 2)
            })

        return jsonify(result), 200

    except Exception as e:
        print(" strategy_analysis error:", e)
        return jsonify({'error': str(e)}), 500

@journal_bp.route('/variables-analysis', methods=['GET'])
@jwt_required()
def variables_analysis():
    """
    Return performance metrics grouped by variable tags for the current user.
    
    Query Parameters:
        from_date: Filter trades on or after this date (YYYY-MM-DD)
        to_date: Filter trades on or before this date (YYYY-MM-DD)
        timeframe: Filter by time period ('30', '90', '365', 'all')
        combine_vars: If 'true', also include variable combinations (default: false)
        combination_level: Number of variables to combine (2-5, default: 2)
    
    Returns:
        JSON response with variable statistics and combinations
    """
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        
        # Get query parameters for filtering
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        timeframe = request.args.get('timeframe', 'all')
        combine_vars = request.args.get('combine_vars', 'false').lower() == 'true'
        combination_level = min(max(int(request.args.get('combination_level', 2)), 2), 5)
        min_trades = max(int(request.args.get('min_trades', 1)), 0)
        
        # Handle combination filtering
        selected_combinations = None
        combinations_param = request.args.get('combinations')
        if combinations_param:
            try:
                selected_combinations = json.loads(combinations_param)
                if not isinstance(selected_combinations, list):
                    selected_combinations = None
            except (json.JSONDecodeError, TypeError):
                selected_combinations = None
        
        # Base query
        query = build_group_aware_query(user_id, profile_id).order_by(JournalEntry.date.asc())
        
        # Apply timeframe filter if provided
        if timeframe and timeframe != 'all':
            try:
                days = int(timeframe)
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                query = query.filter(JournalEntry.date >= cutoff_date)
            except ValueError:
                # If timeframe is not a number, ignore it
                pass
        
        # Apply date filters if provided
        if from_date:
            try:
                from_date = datetime.strptime(from_date, '%Y-%m-%d')
                query = query.filter(JournalEntry.date >= from_date)
            except ValueError:
                return jsonify({'error': 'Invalid from_date format. Use YYYY-MM-DD'}), 400
                
        if to_date:
            try:
                to_date = datetime.strptime(to_date, '%Y-%m-%d')
                query = query.filter(JournalEntry.date <= to_date)
            except ValueError:
                return jsonify({'error': 'Invalid to_date format. Use YYYY-MM-DD'}), 400
        
        # Apply additional filters from AdvancedFilter component
        symbols = request.args.get('symbols')
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
            if symbol_list:
                query = query.filter(JournalEntry.symbol.in_(symbol_list))
        
        directions = request.args.get('directions')
        if directions:
            direction_list = [d.strip() for d in directions.split(',') if d.strip()]
            if direction_list:
                query = query.filter(JournalEntry.direction.in_(direction_list))
        
        strategies = request.args.get('strategies')
        if strategies:
            strategy_list = [s.strip() for s in strategies.split(',') if s.strip()]
            if strategy_list:
                query = query.filter(JournalEntry.strategy.in_(strategy_list))
        
        setups = request.args.get('setups')
        if setups:
            setup_list = [s.strip() for s in setups.split(',') if s.strip()]
            if setup_list:
                query = query.filter(JournalEntry.setup.in_(setup_list))
        
        # P&L range filters
        min_pnl = request.args.get('min_pnl')
        if min_pnl:
            try:
                min_pnl_val = float(min_pnl)
                query = query.filter(JournalEntry.pnl >= min_pnl_val)
            except ValueError:
                pass
        
        max_pnl = request.args.get('max_pnl')
        if max_pnl:
            try:
                max_pnl_val = float(max_pnl)
                query = query.filter(JournalEntry.pnl <= max_pnl_val)
            except ValueError:
                pass
        
        # R:R range filters
        min_rr = request.args.get('min_rr')
        if min_rr:
            try:
                min_rr_val = float(min_rr)
                query = query.filter(JournalEntry.rr >= min_rr_val)
            except ValueError:
                pass
        
        max_rr = request.args.get('max_rr')
        if max_rr:
            try:
                max_rr_val = float(max_rr)
                query = query.filter(JournalEntry.rr <= max_rr_val)
            except ValueError:
                pass
        
        # Import batch filter
        batch_ids = request.args.get('batch_ids')
        if batch_ids:
            try:
                batch_id_list = [int(b.strip()) for b in batch_ids.split(',') if b.strip()]
                if batch_id_list:
                    query = query.filter(JournalEntry.import_batch_id.in_(batch_id_list))
            except ValueError:
                pass
        
        # Variables filter
        variables_param = request.args.get('variables')
        if variables_param:
            try:
                variables_filter = json.loads(variables_param)
                if isinstance(variables_filter, dict):
                    # This will be handled after fetching entries
                    pass
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Get all entries that match the filters
        entries = query.all()
        
        # Apply variables filter if provided (case-insensitive matching for keys and values)
        if variables_param:
            try:
                variables_filter = json.loads(variables_param)
                if isinstance(variables_filter, dict) and variables_filter:
                    filtered_entries = []
                    for entry in entries:
                        # Build a case-insensitive map of all variable-like fields from both sources
                        entry_vars_ci = {}
                        if isinstance(entry.variables, dict):
                            for k, v in entry.variables.items():
                                key_l = str(k).strip().lower()
                                entry_vars_ci[key_l] = v
                        if isinstance(entry.extra_data, dict):
                            for k, v in entry.extra_data.items():
                                key_l = str(k).strip().lower()
                                # Do not override if already present from entry.variables
                                if key_l not in entry_vars_ci:
                                    entry_vars_ci[key_l] = v

                        # Check if entry matches all variable filters
                        matches_all = True
                        for var_name, var_values in variables_filter.items():
                            if not isinstance(var_values, list) or not var_values:
                                continue

                            key_l = str(var_name).strip().lower()
                            raw_value = entry_vars_ci.get(key_l)

                            # Normalize entry values to a lowercase list of strings
                            if raw_value is None:
                                entry_values = []
                            elif isinstance(raw_value, list):
                                entry_values = [str(v).strip().lower() for v in raw_value if v is not None and str(v).strip() != '']
                            else:
                                val_str = str(raw_value).strip()
                                entry_values = [val_str.lower()] if val_str != '' else []

                            # Normalize filter values to lowercase
                            filter_values = [str(v).strip().lower() for v in var_values if v is not None and str(v).strip() != '']

                            # Require at least one match
                            if not any(ev in filter_values for ev in entry_values):
                                matches_all = False
                                break

                        if matches_all:
                            filtered_entries.append(entry)

                    entries = filtered_entries
            except (json.JSONDecodeError, TypeError):
                pass
        
        # If no entries found, return empty result
        if not entries:
            return jsonify({
                'variables': [],
                'combinations': [],
                'stats_summary': {
                    'total_trades': 0,
                    'total_pnl': 0.0,
                    'avg_win_rate': 0.0
                }
            })
            
        variable_stats = {}
        all_variable_names = set()
        processed_entries = 0
        skipped_entries = 0
        
        # Define only the most basic system fields that should be excluded
        # Be more flexible and allow users to create any variable names they want
        system_fields = {
            'trade_id', 'import_batch_id', 'id'  # Only exclude truly system-level fields
        }
        
        # First pass: collect all unique variable names across all entries
        for entry in entries:
            # Skip entries without variables
            if not entry.variables and not entry.extra_data:
                continue
                
            variables = {}
            
            # Primary: Check the variables field
            if entry.variables and isinstance(entry.variables, dict):
                # Only include non-system fields and normalize case
                for k, v in entry.variables.items():
                    k_lower = k.lower()
                    # Skip empty values and system fields
                    if (k_lower not in system_fields and 
                        v is not None and 
                        str(v).strip() != ''):
                        variables[k_lower] = v
                all_variable_names.update(variables.keys())
            
            # Fallback: Check extra_data for variable-like fields
            if entry.extra_data and isinstance(entry.extra_data, dict):
                # Be more flexible - only exclude the most basic system fields
                core_fields = {'id', 'symbol', 'direction', 'entry_price', 'exit_price', 'quantity', 
                             'pnl', 'rr', 'notes', 'created_at', 'updated_at',
                             'trade_id', 'import_batch_id'}
                
                for key, value in entry.extra_data.items():
                    # Only skip core fields and system fields - allow user creativity
                    if (key not in core_fields and 
                        key not in system_fields and
                        value is not None and str(value).strip() != ''):
                        # Preserve original key case
                        all_variable_names.add(key)
        
        # Second pass: process entries with the collected variable names
        for entry in entries:
            # Skip entries without variables
            if not entry.variables and not entry.extra_data:
                skipped_entries += 1
                continue
                
            variables = {}
            
            # Primary: Check the variables field
            if entry.variables and isinstance(entry.variables, dict):
                # Only include non-system fields and normalize case
                for k, v in entry.variables.items():
                    k_lower = k.lower()
                    # Skip empty values and system fields
                    if (k_lower not in system_fields and 
                        v is not None and 
                        str(v).strip() != ''):
                        variables[k_lower] = v
            
            # Fallback: Check extra_data for variable-like fields
            if entry.extra_data and isinstance(entry.extra_data, dict):
                for var_name in all_variable_names:
                    if (var_name in entry.extra_data and 
                        entry.extra_data[var_name] and 
                        var_name not in system_fields):
                        # Only add if not already present from variables field
                        if var_name not in variables:
                            value = entry.extra_data[var_name]
                            # Ensure value is in list format
                            if isinstance(value, list):
                                variables[var_name] = [str(v).strip() for v in value if v and str(v).strip()]
                            else:
                                value_str = str(value).strip()
                                if value_str:
                                    variables[var_name] = [value_str]
            
            # Skip entries with no variables found
            if not variables:
                skipped_entries += 1
                continue
                
            # Ensure all variables from our set are present in this entry (even if empty)
            # Keep original case for better user experience
            processed_entries += 1
            
            # Process each variable in this entry
            for var_name in all_variable_names:
                # Get the value for this variable (case-sensitive)
                value = variables.get(var_name, [])
                
                # Handle both list and string formats
                if isinstance(value, list):
                    tags = [str(v).strip() for v in value if v and str(v).strip()]
                else:
                    value_str = str(value).strip()
                    tags = [value_str] if value_str else []

                for tag in tags:
                    if not tag:
                        continue
                        
                    # Use lowercase variable name for consistency
                    group = f"{var_name}: {tag}"
                    if group not in variable_stats:
                        variable_stats[group] = {
                            'trades': 0,
                            'wins': 0,
                            'losses': 0,
                            'total_rr': 0.0,
                            'total_pnl': 0.0,
                            'gross_profit': 0.0,
                            'gross_loss': 0.0,
                            'win_amounts': [],
                            'loss_amounts': [],
                            'pnl_history': [],
                            'cumulative_pnl': [],
                            'running_pnl': 0.0,
                            'peak': 0.0,
                            'max_drawdown': 0.0,
                            'first_date': None,
                            'last_date': None,
                            'trades_data': []
                        }
                    
                    stats = variable_stats[group]
                    
                    # Track trade dates
                    if entry.date:
                        if stats['first_date'] is None or entry.date < stats['first_date']:
                            stats['first_date'] = entry.date
                        if stats['last_date'] is None or entry.date > stats['last_date']:
                            stats['last_date'] = entry.date
                    
                    # Update trade statistics
                    stats['trades'] += 1
                    stats['total_rr'] += entry.rr or 0.0
                    stats['total_pnl'] += entry.pnl or 0.0
                    stats['running_pnl'] += entry.pnl or 0.0
                    
                    # Track PnL history for drawdown calculation
                    stats['pnl_history'].append({
                        'date': entry.date.isoformat() if entry.date else None,
                        'pnl': entry.pnl or 0.0,
                        'cumulative': stats['running_pnl']
                    })
                    
                    # Update peak and drawdown
                    if stats['running_pnl'] > stats['peak']:
                        stats['peak'] = stats['running_pnl']
                    else:
                        drawdown = stats['peak'] - stats['running_pnl']
                        if drawdown > stats['max_drawdown']:
                            stats['max_drawdown'] = drawdown
                    
                    # Handle win/loss classification (skip zero PnL for win rate calculation)
                    if entry.pnl and entry.pnl != 0:
                        if entry.pnl > 0:
                            stats['wins'] += 1
                            stats['gross_profit'] += entry.pnl
                            stats['win_amounts'].append(entry.pnl)
                        else:
                            stats['losses'] += 1
                            loss = abs(entry.pnl)
                            stats['gross_loss'] += loss
                            stats['loss_amounts'].append(-loss)
                    
                    # Store trade data for later calculations
                    stats['trades_data'].append({
                        'date': entry.date.isoformat() if entry.date else None,
                        'pnl': entry.pnl or 0.0,
                        'rr': entry.rr or 0.0,
                        'symbol': entry.symbol,
                        'direction': entry.direction
                    })
        
        print(f"Variables analysis: processed {processed_entries} entries, skipped {skipped_entries} entries without variables")
        print(f"Found {len(variable_stats)} unique variable combinations")
        
        # Calculate additional metrics and format response
        result = []
        best_metric = {'value': None, 'metric': 'profit_factor', 'variable': None}
        total_trades = 0
        total_pnl = 0.0
        total_win_rate = 0.0
        total_profit_factor = 0.0
        variable_count = 0
        
        for label, data in variable_stats.items():
            wins = data['wins']
            losses = data['losses']
            total = data['trades']
            
            if total == 0:
                continue
                
            # Calculate basic metrics
            win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0
            avg_rr = data['total_rr'] / total if total > 0 else 0.0
            
            # Calculate profit factor
            profit_factor = 0.0
            if data['gross_loss'] > 0:
                profit_factor = data['gross_profit'] / data['gross_loss']
            elif data['gross_profit'] > 0:
                profit_factor = None  # Using None instead of float('inf') for JSON serialization
            
            # Calculate average win/loss
            avg_win = sum(data['win_amounts']) / len(data['win_amounts']) if data['win_amounts'] else 0.0
            avg_loss = sum(data['loss_amounts']) / len(data['loss_amounts']) if data['loss_amounts'] else 0.0
            
            # Calculate max win/loss
            max_win = max(data['win_amounts'], default=0.0)
            max_loss = max(data['loss_amounts'], default=0.0)
            
            # Calculate expectancy
            win_prob = wins / total if total > 0 else 0
            loss_prob = losses / total if total > 0 else 0
            expectancy = (win_prob * avg_win) - (loss_prob * avg_loss)
            
            # Calculate consistency score (0-1, higher is more consistent)
            consistency = 0.0
            if wins > 0 and losses > 0:
                win_std = (sum((x - avg_win) ** 2 for x in data['win_amounts']) / len(data['win_amounts'])) ** 0.5 if data['win_amounts'] else 0
                loss_std = (sum((x - avg_loss) ** 2 for x in data['loss_amounts']) / len(data['loss_amounts'])) ** 0.5 if data['loss_amounts'] else 0
                consistency = 1 / (1 + (win_std / avg_win if avg_win != 0 else 0) + (loss_std / avg_loss if avg_loss != 0 else 0))
            
            # Sort PnL history by date
            sorted_pnl = sorted(data['pnl_history'], key=lambda x: x['date'] or '')
            
            # Prepare cumulative PnL data for charting
            cumulative_pnl = []
            running_total = 0.0
            for trade in sorted_pnl:
                running_total += trade['pnl']
                cumulative_pnl.append({
                    'date': trade['date'],
                    'value': round(running_total, 2)
                })
            
            # Create variable stats object
            var_stats = {
                'variable': label,
                'trades': total,
                'wins': wins,
                'losses': losses,
                'win_rate': round(win_rate, 1),
                'avg_rr': round(avg_rr, 2),
                'pnl': round(data['total_pnl'], 2),
                'profit_factor': round(profit_factor, 2) if profit_factor is not None else None,
                'gross_profit': round(data['gross_profit'], 2),
                'gross_loss': round(data['gross_loss'], 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'max_win': round(max_win, 2),
                'max_loss': round(-max_loss, 2) if max_loss != 0 else 0.0,
                'max_drawdown': round(abs(data['max_drawdown']), 2) if data['max_drawdown'] is not None else 0.0,
                'expectancy': round(expectancy, 2),
                'consistency_score': round(consistency, 2),
                'cumulative_pnl': cumulative_pnl,
                'first_trade_date': data['first_date'].strftime('%Y-%m-%d') if data['first_date'] else None,
                'latest_date': data['last_date'].strftime('%Y-%m-%d') if data['last_date'] else None,
                'is_combination': False,
                'variable_components': [label]
            }
            
            # Track best performing variable by profit factor
            if profit_factor is not None and (best_metric['value'] is None or profit_factor > best_metric['value']):
                best_metric = {
                    'value': profit_factor,
                    'metric': 'profit_factor',
                    'variable': label
                }
            
            # Update summary stats
            total_trades += total
            total_pnl += data['total_pnl']
            total_win_rate += win_rate
            total_profit_factor += profit_factor if profit_factor is not None else 0
            variable_count += 1
            
            result.append(var_stats)
        
        # Calculate averages for summary
        avg_win_rate = total_win_rate / variable_count if variable_count > 0 else 0
        avg_profit_factor = total_profit_factor / variable_count if variable_count > 0 else 0
        
        # Sort results by total PnL (descending) for better display
        result.sort(key=lambda x: x['pnl'], reverse=True)
        
        # Analyze variable combinations if requested
        combinations_result = []
        total_combinations_before_filter = 0  # Initialize the variable
        if combine_vars and len(entries) > 0:
            try:
                combinations_result, total_combinations_before_filter = analyze_variable_combinations(
                    entries, combination_level, min_trades, selected_combinations
                )
                print(f"Generated {len(combinations_result)} variable combinations")
                if selected_combinations:
                    print(f"Filtered to {len(selected_combinations)} selected combinations")
                
                # Add combination stats to the result
                for combo in combinations_result:
                    combo['is_combination'] = True
                    
                    # Update best metric if this combination is better
                    if combo['profit_factor'] is not None and \
                       (best_metric['value'] is None or combo['profit_factor'] > best_metric['value']):
                        best_metric = {
                            'value': combo['profit_factor'],
                            'metric': 'profit_factor',
                            'variable': combo['combination'],
                            'is_combination': True
                        }
                    
                    # Add to summary stats
                    total_trades += combo['trades']
                    total_pnl += combo['pnl']
                    total_win_rate += combo['win_rate']
                    if combo['profit_factor'] is not None:
                        total_profit_factor += combo['profit_factor']
                        variable_count += 1
                
            except NameError as e:
                # Graceful fallback if helper isn't available in the running process
                print(f"⚠️ analyze_variable_combinations not defined at runtime. Falling back to empty combinations. Details: {e}")
                combinations_result = []
                total_combinations_before_filter = 0
            except Exception as e:
                print(f"Error analyzing variable combinations: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Prepare final response
        response = {
            'variables': result,
            'total_combinations': total_combinations_before_filter,
            'combinations': combinations_result[:1000],  # Limit to top 1000 combinations
            'best_performing': best_metric,
            'stats_summary': {
                'total_trades': total_trades,
                'total_pnl': round(total_pnl, 2),
                'avg_win_rate': round(avg_win_rate, 1) if variable_count > 0 else 0.0,
                'avg_profit_factor': round(avg_profit_factor, 2) if variable_count > 0 else 0.0
            },
            'debug_info': {
                'total_entries_checked': len(entries),
                'entries_with_variables': processed_entries,
                'entries_without_variables': skipped_entries,
                'unique_variable_combinations': len(variable_stats),
                'variable_combinations_generated': len(combinations_result)
            }
        }

        print(f"Returning {len(result)} variable analysis results")
        return jsonify(response), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Variables analysis error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@journal_bp.route('/combinations-filter', methods=['GET'])
@jwt_required()
def combinations_filter():
    """
    Get available combinations for the AdvancedFilter component.
    
    Query Parameters:
        combination_level: Number of variables to combine (2-5, default: 2)
        min_trades: Minimum number of trades required (default: 3)
        from_date: Filter trades on or after this date (YYYY-MM-DD)
        to_date: Filter trades on or before this date (YYYY-MM-DD)
        timeframe: Filter by time period ('30', '90', '365', 'all')
        variables: JSON string of variable filters
        symbols: Comma-separated list of symbols
        directions: Comma-separated list of directions
        strategies: Comma-separated list of strategies
        setups: Comma-separated list of setups
        min_pnl: Minimum P&L filter
        max_pnl: Maximum P&L filter
        min_rr: Minimum R:R filter
        max_rr: Maximum R:R filter
        batch_ids: Comma-separated list of import batch IDs
    
    Returns:
        JSON response with available combinations and their performance metrics
    """
    print("🔍 Debug - combinations-filter endpoint called!")
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        
        # Get query parameters
        combination_level = min(max(int(request.args.get('combination_level', 2)), 2), 5)
        min_trades = max(int(request.args.get('min_trades', 3)), 1)
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        timeframe = request.args.get('timeframe', 'all')
        
        # Build base query
        query = JournalEntry.query.filter_by(user_id=user_id, profile_id=profile_id).order_by(JournalEntry.date.asc())
        
        # Apply timeframe filter
        if timeframe and timeframe != 'all':
            try:
                days = int(timeframe)
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                query = query.filter(JournalEntry.date >= cutoff_date)
            except ValueError:
                pass
        
        # Apply date filters
        if from_date:
            try:
                from_date = datetime.strptime(from_date, '%Y-%m-%d')
                query = query.filter(JournalEntry.date >= from_date)
            except ValueError:
                return jsonify({'error': 'Invalid from_date format. Use YYYY-MM-DD'}), 400
                
        if to_date:
            try:
                to_date = datetime.strptime(to_date, '%Y-%m-%d')
                query = query.filter(JournalEntry.date <= to_date)
            except ValueError:
                return jsonify({'error': 'Invalid to_date format. Use YYYY-MM-DD'}), 400
        
        # Apply additional filters
        symbols = request.args.get('symbols')
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
            if symbol_list:
                query = query.filter(JournalEntry.symbol.in_(symbol_list))
        
        directions = request.args.get('directions')
        if directions:
            direction_list = [d.strip() for d in directions.split(',') if d.strip()]
            if direction_list:
                query = query.filter(JournalEntry.direction.in_(direction_list))
        
        strategies = request.args.get('strategies')
        if strategies:
            strategy_list = [s.strip() for s in strategies.split(',') if s.strip()]
            if strategy_list:
                query = query.filter(JournalEntry.strategy.in_(strategy_list))
        
        setups = request.args.get('setups')
        if setups:
            setup_list = [s.strip() for s in setups.split(',') if s.strip()]
            if setup_list:
                query = query.filter(JournalEntry.setup.in_(setup_list))
        
        # P&L range filters
        min_pnl = request.args.get('min_pnl')
        if min_pnl:
            try:
                min_pnl_val = float(min_pnl)
                query = query.filter(JournalEntry.pnl >= min_pnl_val)
            except ValueError:
                pass
        
        max_pnl = request.args.get('max_pnl')
        if max_pnl:
            try:
                max_pnl_val = float(max_pnl)
                query = query.filter(JournalEntry.pnl <= max_pnl_val)
            except ValueError:
                pass
        
        # R:R range filters
        min_rr = request.args.get('min_rr')
        if min_rr:
            try:
                min_rr_val = float(min_rr)
                query = query.filter(JournalEntry.rr >= min_rr_val)
            except ValueError:
                pass
        
        max_rr = request.args.get('max_rr')
        if max_rr:
            try:
                max_rr_val = float(max_rr)
                query = query.filter(JournalEntry.rr <= max_rr_val)
            except ValueError:
                pass
        
        # Import batch filter
        batch_ids = request.args.get('batch_ids')
        if batch_ids:
            try:
                batch_id_list = [int(b.strip()) for b in batch_ids.split(',') if b.strip()]
                if batch_id_list:
                    query = query.filter(JournalEntry.import_batch_id.in_(batch_id_list))
            except ValueError:
                pass
        
        # Get filtered entries
        entries = query.all()
        
        # Debug: Check what's in the entries
        print(f"🔍 Debug - Retrieved {len(entries)} entries from database")
        if entries:
            sample_entry = entries[0]
            print(f"🔍 Debug - Sample entry variables: {getattr(sample_entry, 'variables', 'NO_VARIABLES_ATTR')}")
            print(f"🔍 Debug - Sample entry extra_data: {getattr(sample_entry, 'extra_data', 'NO_EXTRA_DATA_ATTR')}")
            print(f"🔍 Debug - Sample entry hasattr variables: {hasattr(sample_entry, 'variables')}")
            print(f"🔍 Debug - Sample entry hasattr extra_data: {hasattr(sample_entry, 'extra_data')}")
            
            # Check a few more entries to see the pattern
            entries_with_vars = 0
            for i, entry in enumerate(entries[:5]):  # Check first 5 entries
                if hasattr(entry, 'variables') and entry.variables:
                    entries_with_vars += 1
                    print(f"🔍 Debug - Entry {i+1} variables: {entry.variables}")
                if hasattr(entry, 'extra_data') and entry.extra_data:
                    print(f"🔍 Debug - Entry {i+1} extra_data: {entry.extra_data}")
            print(f"🔍 Debug - First 5 entries with variables: {entries_with_vars}")
        
        # Apply variables filter if provided
        variables_param = request.args.get('variables')
        if variables_param:
            try:
                variables_filter = json.loads(variables_param)
                if isinstance(variables_filter, dict) and variables_filter:
                    filtered_entries = []
                    for entry in entries:
                        matches_all = True
                        for var_name, var_values in variables_filter.items():
                            if not isinstance(var_values, list) or not var_values:
                                continue
                            
                            entry_vars = entry.variables or {}
                            if isinstance(entry_vars, dict):
                                entry_value = entry_vars.get(var_name)
                                if entry_value:
                                    if isinstance(entry_value, list):
                                        entry_values = [str(v).strip().lower() for v in entry_value if v]
                                    else:
                                        entry_values = [str(entry_value).strip().lower()]
                                else:
                                    extra_data = entry.extra_data or {}
                                    if isinstance(extra_data, dict):
                                        entry_value = extra_data.get(var_name)
                                        if entry_value:
                                            if isinstance(entry_value, list):
                                                entry_values = [str(v).strip().lower() for v in entry_value if v]
                                            else:
                                                entry_values = [str(entry_value).strip().lower()]
                                        else:
                                            entry_values = []
                                    else:
                                        entry_values = []
                            else:
                                entry_values = []
                            
                            filter_values = [str(v).strip().lower() for v in var_values if v]
                            if not any(ev in filter_values for ev in entry_values):
                                matches_all = False
                                break
                        
                        if matches_all:
                            filtered_entries.append(entry)
                    
                    entries = filtered_entries
            except (json.JSONDecodeError, TypeError):
                pass
        
        # If no entries found, return empty result
        if not entries:
            return jsonify({
                'combinations': [],
                'total_combinations': 0,
                'filtered_entries': 0
            })
        
        # Analyze combinations
        try:
            combinations_result, total_combinations = analyze_variable_combinations(
                entries, combination_level, min_trades
            )
            
            return jsonify({
                'combinations': combinations_result,
                'total_combinations': total_combinations,
                'filtered_entries': len(entries),
                'combination_level': combination_level,
                'min_trades': min_trades
            })
            
        except NameError as e:
            # Graceful fallback if helper isn't available in the running process
            print(f"⚠️ analyze_variable_combinations not defined at runtime. Returning empty combinations. Details: {e}")
            return jsonify({
                'combinations': [],
                'total_combinations': 0,
                'filtered_entries': len(entries),
                'combination_level': combination_level,
                'min_trades': min_trades
            })
        except Exception as e:
            print(f"Error analyzing combinations: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error analyzing combinations: {str(e)}'}), 500
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Combinations filter error: {str(e)}")
        return jsonify({'error': str(e)}), 500
        
@journal_bp.route('/symbol-analysis', methods=['GET'])
@jwt_required()
def symbol_analysis():
    """Return performance metrics grouped by symbol/pair for the current user"""
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        print(f"\n=== Processing symbol analysis for user {user_id}, profile {profile_id} ===")
        
        # Build base query
        base_query = build_group_aware_query(user_id, profile_id)
        
        # Apply filters if provided
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        symbols = request.args.get('symbols')
        directions = request.args.get('directions')
        strategies = request.args.get('strategies')
        setups = request.args.get('setups')
        min_pnl = request.args.get('min_pnl')
        max_pnl = request.args.get('max_pnl')
        min_rr = request.args.get('min_rr')
        max_rr = request.args.get('max_rr')
        batch_ids = request.args.get('batch_ids')
        time_of_day = request.args.get('time_of_day')
        day_of_week = request.args.get('day_of_week')
        month = request.args.get('month')
        year = request.args.get('year')
        variables_param = request.args.get('variables')
        
        # Apply date filters
        if from_date:
            base_query = base_query.filter(JournalEntry.date >= from_date)
        if to_date:
            base_query = base_query.filter(JournalEntry.date <= to_date)
            
        # Apply symbol filter
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(',')]
            base_query = base_query.filter(JournalEntry.symbol.in_(symbol_list))
            
        # Apply direction filter
        if directions:
            direction_list = [d.strip() for d in directions.split(',')]
            base_query = base_query.filter(JournalEntry.direction.in_(direction_list))
            
        # Apply strategy filter
        if strategies:
            strategy_list = [s.strip() for s in strategies.split(',')]
            base_query = base_query.filter(JournalEntry.strategy.in_(strategy_list))
            
        # Apply setup filter
        if setups:
            setup_list = [s.strip() for s in setups.split(',')]
            base_query = base_query.filter(JournalEntry.setup.in_(setup_list))
            
        # Apply PnL range filter
        if min_pnl:
            base_query = base_query.filter(JournalEntry.pnl >= float(min_pnl))
        if max_pnl:
            base_query = base_query.filter(JournalEntry.pnl <= float(max_pnl))
            
        # Apply R:R range filter
        if min_rr:
            base_query = base_query.filter(JournalEntry.rr >= float(min_rr))
        if max_rr:
            base_query = base_query.filter(JournalEntry.rr <= float(max_rr))
            
        # Apply import batch filter
        if batch_ids:
            batch_list = [int(b.strip()) for b in batch_ids.split(',')]
            base_query = base_query.filter(JournalEntry.import_batch_id.in_(batch_list))
            
        # Apply time of day filter
        if time_of_day:
            time_list = [t.strip() for t in time_of_day.split(',')]
            time_conditions = []
            for time_range in time_list:
                if ':' in time_range:
                    start_time, end_time = time_range.split('-')
                    time_conditions.append(
                        JournalEntry.time.between(start_time.strip(), end_time.strip())
                    )
            if time_conditions:
                base_query = base_query.filter(or_(*time_conditions))
                
        # Apply day of week filter
        if day_of_week:
            day_list = [d.strip() for d in day_of_week.split(',')]
            day_conditions = []
            for day in day_list:
                day_conditions.append(extract('dow', JournalEntry.date) == day)
            if day_conditions:
                base_query = base_query.filter(or_(*day_conditions))
                
        # Apply month filter
        if month:
            month_list = [m.strip() for m in month.split(',')]
            month_conditions = []
            for month_val in month_list:
                month_conditions.append(extract('month', JournalEntry.date) == int(month_val))
            if month_conditions:
                base_query = base_query.filter(or_(*month_conditions))
                
        # Apply year filter
        if year:
            year_list = [y.strip() for y in year.split(',')]
            year_conditions = []
            for year_val in year_list:
                year_conditions.append(extract('year', JournalEntry.date) == int(year_val))
            if year_conditions:
                base_query = base_query.filter(or_(*year_conditions))

        entries = base_query.all()

        # Apply variables filter if provided
        if variables_param:
            try:
                variables_filter = json.loads(variables_param)
                if isinstance(variables_filter, dict) and variables_filter:
                    entries = [trade for trade in entries if apply_variables_filter(trade, variables_filter)]
            except (json.JSONDecodeError, TypeError):
                # Ignore malformed variables filter
                pass
        print(f"Found {len(entries)} trades for user {user_id} after filtering")
        symbol_map = {}
        for e in entries:
            sym = (e.symbol or '').upper()
            if not sym:
                continue
            stats = symbol_map.setdefault(sym, {
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'total_rr': 0.0,
                'total_pnl': 0.0,
                'gross_profit': 0.0,
                'gross_loss': 0.0,
                'first_date': None,
                'last_date': None
            })
            # Track earliest and latest trade dates for this symbol
            if e.date:
                if stats['first_date'] is None or e.date < stats['first_date']:
                    stats['first_date'] = e.date
                if stats['last_date'] is None or e.date > stats['last_date']:
                    stats['last_date'] = e.date
            if e.pnl == 0:
                # treat as break-even (ignore for win/loss pct but count trade)
                stats['trades']+=1
                continue
            stats['trades']+=1
            stats['total_rr']+= e.rr or 0.0
            stats['total_pnl'] += e.pnl or 0.0
            if e.pnl > 0:
                stats['wins']+=1
                stats['gross_profit'] += e.pnl
            else:
                stats['losses']+=1
                stats['gross_loss'] += abs(e.pnl)
 
        result = []
        for sym,d in symbol_map.items():
            wins = d['wins']
            losses = d['losses']
            total = d['trades']
            win_rate = (wins / (wins + losses) * 100) if (wins + losses) else 0.0
            avg_rr = d['total_rr'] / total if total else 0.0
            profit_factor = (d['gross_profit'] / d['gross_loss']) if d['gross_loss'] else (float('inf') if d['gross_profit'] else 0.0)
            result.append({
                'symbol': sym,
                'trades': total,
                'win_rate': round(win_rate, 1),
                'avg_rr': round(avg_rr, 2),
                'pnl': round(d['total_pnl'], 2),
                'profit_factor': None if not math.isfinite(profit_factor) else round(profit_factor, 2),
                'gross_profit': round(d['gross_profit'], 2),
                'gross_loss': round(d['gross_loss'], 2),
                'first_trade_date': d['first_date'].strftime('%Y-%m-%d') if d['first_date'] else None,
                'latest_date': d['last_date'].strftime('%Y-%m-%d') if d['last_date'] else None
            })
 
        return jsonify(result), 200
    except Exception as e:
        print(' symbol_analysis error:', e)
        return jsonify({'error': str(e)}), 500


# ─── Risk Summary ───────────────────────────────────────────────────────────
@journal_bp.route('/risk-summary', methods=['GET'])
@jwt_required()
def risk_summary():
    """Return distribution of R-multiples and risk stats for the current user.

    Response JSON
    {
        "r_multiples": [...],
        "avg_risk": 0.8,
        "avg_r_multiple": 0.25,
        "max_risk": 2.1,
        "over_risk_count": 3,
        "total_trades": 42
    }
    Optional query param:
      max_allowed (float) – threshold to flag trades whose risk exceeds this value (default 1.0)
    """
    try:
        user_id = int(get_jwt_identity())
        max_allowed = float(request.args.get('max_allowed', 1.0))

        # Fetch only the columns we need for performance
        trades = (
            JournalEntry.query
            .with_entities(JournalEntry.rr, JournalEntry.risk_amount)
            .filter_by(user_id=user_id)
            .all()
        )

        if not trades:
            return jsonify({
                'r_multiples': [],
                'avg_risk': None,
                'avg_r_multiple': None,
                'max_risk': None,
                'over_risk_count': 0,
                'total_trades': 0
            }), 200

        r_multiples = [float(t.rr) for t in trades if t.rr is not None]
        risks = [float(t.risk_amount) for t in trades if t.risk_amount is not None]

        avg_risk = sum(risks) / len(risks) if risks else None
        avg_r_multiple = sum(r_multiples) / len(r_multiples) if r_multiples else None
        max_risk = max(risks) if risks else None
        over_risk_count = sum(1 for r in risks if r > max_allowed)

        return jsonify({
            'r_multiples': r_multiples,
            'avg_risk': round(avg_risk, 4) if avg_risk is not None else None,
            'avg_r_multiple': round(avg_r_multiple, 4) if avg_r_multiple is not None else None,
            'max_risk': max_risk,
            'over_risk_count': over_risk_count,
            'total_trades': len(trades)
        }), 200

    except Exception as e:
        print("risk_summary error:", e)
        return jsonify({'error': str(e)}), 500

# ─── Health Check ─────────────────────────────────────────────────────────
@journal_bp.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'Backend is running'}), 200

# ─── Risk/Reward Amelioration Analysis ─────────────────────────────────────
@journal_bp.route('/risk-reward-amelioration', methods=['GET'])
@jwt_required()
def risk_reward_amelioration():
    """Return detailed risk/reward analysis for amelioration page.
    
    Response JSON:
    {
        "trades": [
            {
                "id": 1,
                "symbol": "BTC/USD",
                "direction": "long",
                "entry_price": 50000,
                "exit_price": 52000,
                "pnl": 2000,
                "rr": 2.5,
                "date": "2023-01-01T10:00:00",
                "strategy": "breakout"
            }
        ],
        "summary": {
            "total_trades": 100,
            "avg_rr": 1.8,
            "best_rr": 5.2,
            "worst_rr": 0.3,
            "profitable_trades": 65,
            "win_rate": 65.0
        },
        "performance_by_rr": [
            {
                "rr_range": "0-1",
                "trades": 20,
                "pnl": -500,
                "win_rate": 30.0
            }
        ]
    }
    """
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        
        # Get filter parameters
        symbol_filter = request.args.get('symbol')
        strategy_filter = request.args.get('strategy')
        setup_filter = request.args.get('setup')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Build query
        query = JournalEntry.query.filter_by(user_id=user_id, profile_id=profile_id)
        
        if symbol_filter:
            query = query.filter(JournalEntry.symbol == symbol_filter)
        if strategy_filter:
            query = query.filter(JournalEntry.strategy == strategy_filter)
        if setup_filter:
            query = query.filter(JournalEntry.setup == setup_filter)
        if start_date:
            query = query.filter(JournalEntry.date >= start_date)
        if end_date:
            query = query.filter(JournalEntry.date <= end_date)
            
        trades = query.order_by(JournalEntry.date.desc()).all()
        
        if not trades:
            return jsonify({
                'trades': [],
                'summary': {
                    'total_trades': 0,
                    'avg_rr': 0,
                    'best_rr': 0,
                    'worst_rr': 0,
                    'profitable_trades': 0,
                    'win_rate': 0
                },
                'performance_by_rr': []
            }), 200
        
        # Process trades data
        trades_data = []
        rr_values = []
        profitable_trades = 0
        
        for trade in trades:
            if trade.rr is not None:
                rr_values.append(float(trade.rr))
                if trade.pnl > 0:
                    profitable_trades += 1
                    
                trades_data.append({
                    'id': trade.id,
                    'symbol': trade.symbol,
                    'direction': trade.direction,
                    'entry_price': trade.entry_price,
                    'exit_price': trade.exit_price,
                    'pnl': trade.pnl,
                    'rr': float(trade.rr),
                    'date': trade.date.isoformat() if trade.date else None,
                    'strategy': trade.strategy,
                    'setup': trade.setup
                })
        
        # Calculate summary statistics
        total_trades = len(trades_data)
        avg_rr = sum(rr_values) / len(rr_values) if rr_values else 0
        best_rr = max(rr_values) if rr_values else 0
        worst_rr = min(rr_values) if rr_values else 0
        win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Group performance by RR ranges
        performance_by_rr = []
        rr_ranges = [
            (0, 1, "0-1"),
            (1, 1.5, "1-1.5"),
            (1.5, 2, "1.5-2"),
            (2, 3, "2-3"),
            (3, 5, "3-5"),
            (5, float('inf'), "5+")
        ]
        
        for min_rr, max_rr, range_label in rr_ranges:
            range_trades = [t for t in trades_data if min_rr <= t['rr'] < max_rr]
            if range_trades:
                range_pnl = sum(t['pnl'] for t in range_trades)
                range_wins = sum(1 for t in range_trades if t['pnl'] > 0)
                range_win_rate = (range_wins / len(range_trades) * 100) if range_trades else 0
                
                performance_by_rr.append({
                    'rr_range': range_label,
                    'trades': len(range_trades),
                    'pnl': round(range_pnl, 2),
                    'win_rate': round(range_win_rate, 1),
                    'avg_rr': round(sum(t['rr'] for t in range_trades) / len(range_trades), 2)
                })
        
        return jsonify({
            'trades': trades_data,
            'summary': {
                'total_trades': total_trades,
                'avg_rr': round(avg_rr, 2),
                'best_rr': round(best_rr, 2),
                'worst_rr': round(worst_rr, 2),
                'profitable_trades': profitable_trades,
                'win_rate': round(win_rate, 1)
            },
            'performance_by_rr': performance_by_rr
        }), 200
        
    except Exception as e:
        print("risk_reward_amelioration error:", e)
        return jsonify({'error': str(e)}), 500

# ─── Performance Highlights ────────────────────────────────────────────────
@journal_bp.route('/performance-highlights', methods=['GET'])
@jwt_required()
def performance_highlights():
    """
    Return key performance highlights including best setup, best instrument, and best time of day.
    
    Response format:
    {
        "best_setup": {
            "name": "Setup Name",
            "pnl": 1234.56,
            "win_rate": 75.5,
            "trades": 12
        },
        "best_instrument": {
            "symbol": "BTC/USD",
            "pnl": 5678.90,
            "win_rate": 65.2,
            "trades": 23
        },
        "best_time_of_day": {
            "hour": 10,
            "formatted_time": "10:00 AM",
            "pnl": 3456.78,
            "win_rate": 72.3,
            "trades": 15
        },
        "hourly_performance": [
            {"hour": 0, "pnl": 100, "trades": 5, "win_rate": 60.0},
            ...
        ],
        "monthly_performance": [
            {
                "id": "2023-01",
                "name": "January 2023",
                "trades": 42,
                "return": 1234.56,
                "win_rate": 65.5,
                "weeklyData": [
                    {
                        "week": "2023-01",
                        "week_num": 1,
                        "year": 2023,
                        "start_date": "2023-01-01",
                        "end_date": "2023-01-07",
                        "formatted_range": "Jan 01 - Jan 07, 2023",
                        "pnl": 123.45,
                        "win_rate": 60.0,
                        "trades": 5
                    },
                    ...
                ]
            },
            ...
        ],
        "weekly_performance": [
            {
                "week": "2023-01",
                "week_num": 1,
                "year": 2023,
                "start_date": "2023-01-01",
                "end_date": "2023-01-07",
                "formatted_range": "Jan 01 - Jan 07, 2023",
                "pnl": 123.45,
                "win_rate": 60.0,
                "trades": 5
            },
            ...
        ]
    }
    """
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        print(f"\n=== Processing performance highlights for user {user_id}, profile {profile_id} ===")
        
        # Debug: Log all incoming filter parameters
        print(f"All request args: {dict(request.args)}")
        
        # Build base query
        query = JournalEntry.query.filter_by(user_id=user_id, profile_id=profile_id).order_by(JournalEntry.date.asc())
        
        # Apply filters if provided
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        symbols = request.args.get('symbols')
        directions = request.args.get('directions')
        strategies = request.args.get('strategies')
        setups = request.args.get('setups')
        min_pnl = request.args.get('min_pnl')
        max_pnl = request.args.get('max_pnl')
        min_rr = request.args.get('min_rr')
        max_rr = request.args.get('max_rr')
        batch_ids = request.args.get('batch_ids')
        variables_param = request.args.get('variables')
        
        # Debug: Log individual filter values
        print(f"Filter values: from_date={from_date}, to_date={to_date}, symbols={symbols}, strategies={strategies}, setups={setups}, min_pnl={min_pnl}, max_pnl={max_pnl}")
        
        # Apply date filters
        if from_date:
            try:
                from_date = datetime.strptime(from_date, '%Y-%m-%d')
                query = query.filter(JournalEntry.date >= from_date)
            except ValueError:
                pass
                
        if to_date:
            try:
                to_date = datetime.strptime(to_date, '%Y-%m-%d')
                query = query.filter(JournalEntry.date <= to_date)
            except ValueError:
                pass
        
        # Apply symbol filter
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
            if symbol_list:
                query = query.filter(JournalEntry.symbol.in_(symbol_list))
        
        # Apply direction filter
        if directions:
            direction_list = [d.strip() for d in directions.split(',') if d.strip()]
            if direction_list:
                query = query.filter(JournalEntry.direction.in_(direction_list))
        
        # Apply strategy filter
        if strategies:
            strategy_list = [s.strip() for s in strategies.split(',') if s.strip()]
            if strategy_list:
                query = query.filter(JournalEntry.strategy.in_(strategy_list))
        
        # Apply setup filter
        if setups:
            setup_list = [s.strip() for s in setups.split(',') if s.strip()]
            if setup_list:
                query = query.filter(JournalEntry.setup.in_(setup_list))
        
        # Apply P&L range filters
        if min_pnl:
            try:
                min_pnl_val = float(min_pnl)
                query = query.filter(JournalEntry.pnl >= min_pnl_val)
            except ValueError:
                pass
        
        if max_pnl:
            try:
                max_pnl_val = float(max_pnl)
                query = query.filter(JournalEntry.pnl <= max_pnl_val)
            except ValueError:
                pass
        
        # Apply R:R range filters
        if min_rr:
            try:
                min_rr_val = float(min_rr)
                query = query.filter(JournalEntry.rr >= min_rr_val)
            except ValueError:
                pass
        
        if max_rr:
            try:
                max_rr_val = float(max_rr)
                query = query.filter(JournalEntry.rr <= max_rr_val)
            except ValueError:
                pass
        
        # Apply import batch filter
        if batch_ids:
            try:
                batch_id_list = [int(b.strip()) for b in batch_ids.split(',') if b.strip()]
                if batch_id_list:
                    query = query.filter(JournalEntry.import_batch_id.in_(batch_id_list))
            except ValueError:
                pass
        
        # Get filtered entries
        entries = query.all()
        print(f"Found {len(entries)} trades for user {user_id} after filtering")
        
        # Apply variables filter if provided (post-query filtering)
        if variables_param:
            try:
                variables_filter = json.loads(variables_param)
                if isinstance(variables_filter, dict) and variables_filter:
                    filtered_entries = []
                    for entry in entries:
                        matches_all = True
                        for var_name, var_values in variables_filter.items():
                            if not isinstance(var_values, list) or not var_values:
                                continue
                            
                            entry_vars = entry.variables or {}
                            if isinstance(entry_vars, dict):
                                entry_value = entry_vars.get(var_name)
                                if entry_value:
                                    if isinstance(entry_value, list):
                                        entry_values = [str(v).strip().lower() for v in entry_value if v]
                                    else:
                                        entry_values = [str(entry_value).strip().lower()]
                                else:
                                    extra_data = entry.extra_data or {}
                                    if isinstance(extra_data, dict):
                                        entry_value = extra_data.get(var_name)
                                        if entry_value:
                                            if isinstance(entry_value, list):
                                                entry_values = [str(v).strip().lower() for v in entry_value if v]
                                            else:
                                                entry_values = [str(entry_value).strip().lower()]
                                        else:
                                            entry_values = []
                                    else:
                                        entry_values = []
                            else:
                                entry_values = []
                            
                            filter_values = [str(v).strip().lower() for v in var_values if v]
                            if not any(ev in filter_values for ev in entry_values):
                                matches_all = False
                                break
                        
                        if matches_all:
                            filtered_entries.append(entry)
                    
                    entries = filtered_entries
                    print(f"After variables filtering: {len(entries)} trades")
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error parsing variables filter: {e}")
                # Continue without variables filter if there's an error
        
        if not entries:
            print("No trades found for user, returning empty response")
            return jsonify({
                'best_setup': {'name': 'No data', 'pnl': 0, 'win_rate': 0, 'trades': 0},
                'best_instrument': {'symbol': 'No data', 'pnl': 0, 'win_rate': 0, 'trades': 0},
                'best_time_of_day': {'hour': 0, 'formatted_time': 'No data', 'pnl': 0, 'win_rate': 0, 'trades': 0},
                'best_week': {'week': 'No data', 'formatted_range': 'No data', 'pnl': 0, 'win_rate': 0, 'trades': 0},
                'best_month': {'id': 'no-data', 'name': 'No data', 'trades': 0, 'return': 0, 'win_rate': 0},
                'hourly_performance': [],
                'monthly_performance': [],
                'weekly_performance': []
            })
        
        print(f"Sample entry data: {entries[0].__dict__ if entries else 'No entries'}")
        
        # Helper function to calculate win rate
        def calculate_win_rate(trades):
            if not trades:
                return 0.0
            wins = sum(1 for t in trades if t.pnl > 0)
            return (wins / len(trades)) * 100
        
        # Initialize data structures
        setup_stats = {}
        instrument_stats = {}
        hourly_stats = {hour: [] for hour in range(24)}
        weekly_stats = {}
        monthly_stats = {}
        
        # Analyze trades
        for entry in entries:
            # Setup analysis - convert list to string if needed
            setup_raw = (entry.variables or {}).get('setup', 'No Setup')
            if isinstance(setup_raw, list):
                setup = str(setup_raw)
            else:
                setup = str(setup_raw)
            if setup not in setup_stats:
                setup_stats[setup] = []
            setup_stats[setup].append(entry)
            
            # Instrument analysis
            symbol = entry.symbol
            if symbol not in instrument_stats:
                instrument_stats[symbol] = []
            instrument_stats[symbol].append(entry)
            
            # Hourly analysis
            hour = entry.date.hour
            hourly_stats[hour].append(entry)
            
            # Weekly analysis
            week_key = f"{entry.date.isocalendar().year}-{entry.date.isocalendar().week:02d}"
            if week_key not in weekly_stats:
                weekly_stats[week_key] = {'trades': [], 'pnl': 0, 'wins': 0}
            weekly_stats[week_key]['trades'].append(entry)
            weekly_stats[week_key]['pnl'] += entry.pnl or 0
            if (entry.pnl or 0) > 0:
                weekly_stats[week_key]['wins'] += 1
            
            # Monthly analysis
            month_key = entry.date.strftime('%Y-%m')
            if month_key not in monthly_stats:
                monthly_stats[month_key] = {'trades': [], 'pnl': 0, 'wins': 0, 'weeks': {}}
            
            # Track weekly data within month
            if week_key not in monthly_stats[month_key]['weeks']:
                monthly_stats[month_key]['weeks'][week_key] = {'trades': [], 'pnl': 0, 'wins': 0}
                
            monthly_stats[month_key]['trades'].append(entry)
            monthly_stats[month_key]['pnl'] += entry.pnl or 0
            monthly_stats[month_key]['weeks'][week_key]['trades'].append(entry)
            monthly_stats[month_key]['weeks'][week_key]['pnl'] += entry.pnl or 0
            if (entry.pnl or 0) > 0:
                monthly_stats[month_key]['wins'] += 1
                monthly_stats[month_key]['weeks'][week_key]['wins'] += 1
        
        # Find best setup
        best_setup = None
        for setup, trades in setup_stats.items():
            total_pnl = sum(t.pnl or 0 for t in trades)
            win_rate = calculate_win_rate(trades)
            if best_setup is None or total_pnl > best_setup['pnl']:
                best_setup = {
                    'name': setup,
                    'pnl': round(total_pnl, 2),
                    'win_rate': round(win_rate, 1),
                    'trades': len(trades)
                }
        
        # Find best instrument
        best_instrument = None
        for symbol, trades in instrument_stats.items():
            total_pnl = sum(t.pnl or 0 for t in trades)
            win_rate = calculate_win_rate(trades)
            if best_instrument is None or total_pnl > best_instrument['pnl']:
                best_instrument = {
                    'symbol': symbol,
                    'pnl': round(total_pnl, 2),
                    'win_rate': round(win_rate, 1),
                    'trades': len(trades)
                }
        
        # Process hourly performance
        hourly_performance = []
        best_hour = None
        for hour, trades in hourly_stats.items():
            if not trades:
                hourly_performance.append({
                    'hour': hour,
                    'formatted_time': f"{hour:02d}:00",
                    'pnl': 0,
                    'win_rate': 0,
                    'trades': 0
                })
                continue
                
            total_pnl = sum(t.pnl or 0 for t in trades)
            win_rate = calculate_win_rate(trades)
            
            hour_data = {
                'hour': hour,
                'formatted_time': f"{hour:02d}:00",
                'pnl': round(total_pnl, 2),
                'win_rate': round(win_rate, 1),
                'trades': len(trades)
            }
            hourly_performance.append(hour_data)
            
            if best_hour is None or total_pnl > best_hour['pnl']:
                best_hour = hour_data
        
        # Process weekly performance
        weekly_performance = []
        best_week = None
        for week_key, week_data in weekly_stats.items():
            year, week_num = map(int, week_key.split('-'))
            week_start = datetime.strptime(f"{year}-{week_num}-1", "%Y-%W-%w")
            week_end = week_start + timedelta(days=6.9)
            
            week_trades = week_data['trades']
            total_pnl = week_data['pnl']
            win_rate = (week_data['wins'] / len(week_trades) * 100) if week_trades else 0
            
            week_metrics = {
                'week': week_key,
                'week_num': week_num,
                'year': year,
                'start_date': week_start.strftime('%Y-%m-%d'),
                'end_date': week_end.strftime('%Y-%m-%d'),
                'formatted_range': f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}",
                'pnl': round(total_pnl, 2),
                'win_rate': round(win_rate, 1),
                'trades': len(week_trades)
            }
            weekly_performance.append(week_metrics)
            
            if best_week is None or total_pnl > best_week['pnl']:
                best_week = week_metrics
        
        # Sort weekly performance by date (newest first)
        weekly_performance.sort(key=lambda x: x['start_date'], reverse=True)
        
        # Process monthly performance
        monthly_performance = []
        best_month = None
        print(f"\nProcessing monthly stats. Found {len(monthly_stats)} months of data")
        
        for month_key, month_data in sorted(monthly_stats.items(), reverse=True):
            print(f"\nProcessing month: {month_key}")
            print(f"Month data: {month_data}")
            
            try:
                month_date = datetime.strptime(month_key + '-01', '%Y-%m-%d')
                month_name = month_date.strftime('%B %Y')
                print(f"Formatted month name: {month_name}")
            except Exception as e:
                print(f"Error parsing month {month_key}: {str(e)}")
                continue
            
            month_trades = month_data['trades']
            total_pnl = month_data['pnl']
            win_rate = (month_data['wins'] / len(month_trades) * 100) if month_trades else 0
            
            # Process weekly data for this month
            weekly_data = []
            print(f"  Found {len(month_data.get('weeks', {}))} weeks in month {month_key}")
            
            for week_key, week_data in month_data.get('weeks', {}).items():
                print(f"  Processing week: {week_key}")
                print(f"  Week data: {week_data}")
                
                try:
                    year, week_num = map(int, week_key.split('-'))
                    week_start = datetime.strptime(f"{year}-{week_num}-1", "%Y-%W-%w")
                    week_end = week_start + timedelta(days=6.9)
                    print(f"  Week range: {week_start.date()} to {week_end.date()}")
                except Exception as e:
                    print(f"  Error processing week {week_key}: {str(e)}")
                    continue
                
                week_trades = week_data['trades']
                week_pnl = week_data['pnl']
                week_win_rate = (week_data['wins'] / len(week_trades) * 100) if week_trades else 0
                
                weekly_data.append({
                    'week': week_key,
                    'week_num': week_num,
                    'year': year,
                    'start_date': week_start.strftime('%Y-%m-%d'),
                    'end_date': week_end.strftime('%Y-%m-%d'),
                    'formatted_range': f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}",
                    'pnl': round(week_pnl, 2),
                    'win_rate': round(week_win_rate, 1),
                    'trades': len(week_trades)
                })
            
            # Sort weekly data by date (newest first)
            weekly_data.sort(key=lambda x: x['start_date'], reverse=True)
            
            month_metrics = {
                'id': month_key,
                'name': month_name,
                'trades': len(month_trades),
                'return': round(total_pnl, 2),
                'win_rate': round(win_rate, 1),
                'weeklyData': weekly_data
            }
            monthly_performance.append(month_metrics)
            
            if best_month is None or total_pnl > best_month['return']:
                best_month = month_metrics
        
        # Prepare the response
        response = {
            'best_setup': best_setup or {
                'name': 'No setups found',
                'pnl': 0,
                'win_rate': 0,
                'trades': 0
            },
            'best_instrument': best_instrument or {
                'symbol': 'No instruments found',
                'pnl': 0,
                'win_rate': 0,
                'trades': 0
            },
            'best_time_of_day': best_hour or {
                'hour': 0,
                'formatted_time': 'No data',
                'pnl': 0,
                'win_rate': 0,
                'trades': 0
            },
            'best_week': best_week or {
                'week': 'No data',
                'formatted_range': 'No data',
                'pnl': 0,
                'win_rate': 0,
                'trades': 0
            },
            'best_month': best_month or {
                'id': 'no-data',
                'name': 'No data',
                'trades': 0,
                'return': 0,
                'win_rate': 0
            },
            'hourly_performance': hourly_performance,
            'monthly_performance': monthly_performance,
            'weekly_performance': weekly_performance
        }
        
        print(f"Performance highlights response: {response}")
        print(f"Weekly performance length: {len(weekly_performance)}")
        print(f"Hourly performance length: {len(hourly_performance)}")
        print(f"Monthly performance length: {len(monthly_performance)}")
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Error in performance_highlights: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to generate performance highlights: {str(e)}"}), 500


@journal_bp.route('/report-data', methods=['GET'])
@jwt_required()
def report_data():
    """Return a JSON payload with all analytics needed for report generation.
    Combines overall stats, symbol, strategy and tag breakdown in one call so the
    frontend can fetch once and build a PDF/HTML report.
    """
    try:
        # Reuse existing helper endpoints internally (call their functions) instead
        # of making HTTP requests.
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)

        # Build base query
        query = JournalEntry.query.filter_by(user_id=user_id, profile_id=profile_id).order_by(JournalEntry.date.asc())
        
        # Apply filters if provided
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        symbols = request.args.get('symbols')
        directions = request.args.get('directions')
        strategies = request.args.get('strategies')
        setups = request.args.get('setups')
        min_pnl = request.args.get('min_pnl')
        max_pnl = request.args.get('max_pnl')
        min_rr = request.args.get('min_rr')
        max_rr = request.args.get('max_rr')
        batch_ids = request.args.get('batch_ids')
        variables_param = request.args.get('variables')
        
        # Apply date filters
        if from_date:
            try:
                from_date = datetime.strptime(from_date, '%Y-%m-%d')
                query = query.filter(JournalEntry.date >= from_date)
            except ValueError:
                pass
                
        if to_date:
            try:
                to_date = datetime.strptime(to_date, '%Y-%m-%d')
                query = query.filter(JournalEntry.date <= to_date)
            except ValueError:
                pass
        
        # Apply symbol filter
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
            if symbol_list:
                query = query.filter(JournalEntry.symbol.in_(symbol_list))
        
        # Apply direction filter
        if directions:
            direction_list = [d.strip() for d in directions.split(',') if d.strip()]
            if direction_list:
                query = query.filter(JournalEntry.direction.in_(direction_list))
        
        # Apply strategy filter
        if strategies:
            strategy_list = [s.strip() for s in strategies.split(',') if s.strip()]
            if strategy_list:
                query = query.filter(JournalEntry.strategy.in_(strategy_list))
        
        # Apply setup filter
        if setups:
            setup_list = [s.strip() for s in setups.split(',') if s.strip()]
            if setup_list:
                query = query.filter(JournalEntry.setup.in_(setup_list))
        
        # Apply P&L range filters
        if min_pnl:
            try:
                min_pnl_val = float(min_pnl)
                query = query.filter(JournalEntry.pnl >= min_pnl_val)
            except ValueError:
                pass
        
        if max_pnl:
            try:
                max_pnl_val = float(max_pnl)
                query = query.filter(JournalEntry.pnl <= max_pnl_val)
            except ValueError:
                pass
        
        # Apply R:R range filters
        if min_rr:
            try:
                min_rr_val = float(min_rr)
                query = query.filter(JournalEntry.rr >= min_rr_val)
            except ValueError:
                pass
        
        if max_rr:
            try:
                max_rr_val = float(max_rr)
                query = query.filter(JournalEntry.rr <= max_rr_val)
            except ValueError:
                pass
        
        # Apply import batch filter
        if batch_ids:
            try:
                batch_id_list = [int(b.strip()) for b in batch_ids.split(',') if b.strip()]
                if batch_id_list:
                    query = query.filter(JournalEntry.import_batch_id.in_(batch_id_list))
            except ValueError:
                pass
        
        # Get filtered entries
        entries = query.all()
        
        # Apply variables filter if provided (post-query filtering)
        if variables_param:
            try:
                variables_filter = json.loads(variables_param)
                if isinstance(variables_filter, dict) and variables_filter:
                    filtered_entries = []
                    for entry in entries:
                        matches_all = True
                        for var_name, var_values in variables_filter.items():
                            if not isinstance(var_values, list) or not var_values:
                                continue
                            
                            entry_vars = entry.variables or {}
                            if isinstance(entry_vars, dict):
                                entry_value = entry_vars.get(var_name)
                                if entry_value:
                                    if isinstance(entry_value, list):
                                        entry_values = [str(v).strip().lower() for v in entry_value if v]
                                    else:
                                        entry_values = [str(entry_value).strip().lower()]
                                else:
                                    extra_data = entry.extra_data or {}
                                    if isinstance(extra_data, dict):
                                        entry_value = extra_data.get(var_name)
                                        if entry_value:
                                            if isinstance(entry_value, list):
                                                entry_values = [str(v).strip().lower() for v in entry_value if v]
                                            else:
                                                entry_values = [str(entry_value).strip().lower()]
                                        else:
                                            entry_values = []
                                    else:
                                        entry_values = []
                            else:
                                entry_values = []
                            
                            filter_values = [str(v).strip().lower() for v in var_values if v]
                            if not any(ev in filter_values for ev in entry_values):
                                matches_all = False
                                break
                        
                        if matches_all:
                            filtered_entries.append(entry)
                    
                    entries = filtered_entries
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error parsing variables filter: {e}")
                # Continue without variables filter if there's an error

        # Overall stats (reuse logic from stats() but simplify)
        total_trades = len(entries)
        total_pnl = sum(e.pnl or 0.0 for e in entries)
        wins = [e for e in entries if (e.pnl or 0.0) > 0]
        losses = [e for e in entries if (e.pnl or 0.0) < 0]
        win_rate = (len(wins) / total_trades * 100) if total_trades else 0.0
        avg_rr = (sum(e.rr or 0.0 for e in entries) / total_trades) if total_trades else 0.0

        # Symbol, strategy, tag breakdowns by calling internal funcs directly
        symbol_json, _ = symbol_analysis().__wrapped__(symbol_analysis) if False else (None, None)

        # Instead of hack, we'll replicate small logic quickly using earlier stats_map
        # Symbol map
        sym_map = {}
        for e in entries:
            sym = (e.symbol or '').upper()
            if not sym:
                continue
            d = sym_map.setdefault(sym, {'trades':0,'wins':0,'total_rr':0.0,'total_pnl':0.0})
            d['trades']+=1
            d['total_rr']+= e.rr or 0.0
            d['total_pnl'] += e.pnl or 0.0
            if (e.pnl or 0.0)>0:
                d['wins']+=1
        symbol_stats=[]
        for sym,d in sym_map.items():
            total=d['trades']; win_rate_s=(d['wins']/total*100) if total else 0.0
            symbol_stats.append({
                'symbol':sym,
                'trades':total,
                'win_rate':round(win_rate_s,1),
                'avg_rr':round(d['total_rr']/total if total else 0.0,2),
                'pnl':round(d['total_pnl'],2)
            })

        # Strategy map
        strat_map={}
        for e in entries:
            strat=e.strategy or 'Unspecified'
            d=strat_map.setdefault(strat,{'trades':0,'wins':0,'total_rr':0.0,'total_pnl':0.0})
            d['trades']+=1
            d['total_rr']+= e.rr or 0.0
            d['total_pnl']+= e.pnl or 0.0
            if (e.pnl or 0.0)>0:
                d['wins']+=1
        strategy_stats=[]
        for strat,d in strat_map.items():
            total=d['trades']; win_rate_s=(d['wins']/total*100) if total else 0.0
            strategy_stats.append({
                'strategy':strat,
                'trades':total,
                'win_rate':round(win_rate_s,1),
                'avg_rr':round(d['total_rr']/total if total else 0.0,2),
                'pnl':round(d['total_pnl'],2)
            })

        # Tag breakdown reuse logic from tag_breakdown above
        tag_data = tag_breakdown().__wrapped__(tag_breakdown) if False else None
        # We'll replicate quickly
        tag_stats_ret = []
        tag_map={}
        for e in entries:
            vars = e.variables or {}
            pnl_val = e.pnl or 0.0
            rr_val = e.rr or 0.0
            is_win = pnl_val>0
            for k,v in vars.items():
                # Convert list values to strings to avoid unhashable type error
                if isinstance(v, list):
                    labels = [str(item) for item in v]
                else:
                    labels = [str(v)]
                for lab in labels:
                    t=tag_map.setdefault(k,{}).setdefault(lab,{'trades':0,'wins':0,'total_pnl':0.0,'total_rr':0.0})
                    t['trades']+=1
                    t['total_pnl']+=pnl_val
                    t['total_rr']+=rr_val
                    if is_win:
                        t['wins']+=1
        for k,lab_dict in tag_map.items():
            items=[]
            for lab,agg in lab_dict.items():
                tr=agg['trades']; win=(agg['wins']/tr*100) if tr else 0.0
                items.append({'label':lab,'trades':tr,'win_rate':round(win,1),'avg_pnl':round(agg['total_pnl']/tr if tr else 0.0,2),'avg_rr':round(agg['total_rr']/tr if tr else 0.0,2)})
            items.sort(key=lambda x:x['trades'],reverse=True)
            tag_stats_ret.append({'tag':k,'items':items})
        tag_stats_ret.sort(key=lambda g:sum(i['trades'] for i in g['items']),reverse=True)

        return jsonify({
            'overall': {
                'total_trades': total_trades,
                'total_pnl': round(total_pnl,2),
                'win_rate': round(win_rate,1),
                'avg_rr': round(avg_rr,2)
            },
            'symbols': symbol_stats,
            'strategies': strategy_stats,
            'tags': tag_stats_ret
        }), 200

    except Exception as e:
        print(' report_data error:', e)
        return jsonify({'error': str(e)}), 500

# ─── Exit Analysis ────────────────────────────────────────────────────────────

@journal_bp.route('/trade/<int:trade_id>/exit-analysis', methods=['GET'])
@jwt_required()
def exit_analysis(trade_id):
    """
    Fetch price data for a specific trade to analyze price movement relative to SL/TP.
    
    Returns:
        JSON with price data, entry/exit points, and SL/TP levels
    """
    try:
        user_id = int(get_jwt_identity())
        print(f"Exit analysis requested for trade {trade_id} by user {user_id}")
        
        # Get the trade
        trade = JournalEntry.query.filter_by(id=trade_id, user_id=user_id).first()
        if not trade:
            print(f"Trade {trade_id} not found for user {user_id}")
            return jsonify({"error": "Trade not found or access denied"}), 404
        
        # Skip if no symbol or entry/exit dates
        if not trade.symbol or not trade.date or not trade.exit_price:
            print(f"Incomplete trade data for analysis: {trade_id}")
            return jsonify({"error": "Incomplete trade data for analysis"}), 400
            
        # Convert symbol to yfinance format (e.g., BTC-USD for crypto)
        symbol = trade.symbol.replace('/', '-')
        if trade.instrument_type == 'crypto':
            symbol = f"{symbol}"
        
        # Set date range (1 day before entry to 1 day after exit)
        start_date = (trade.date - timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = (trade.updated_at if hasattr(trade, 'updated_at') else trade.date) + timedelta(days=1)
        end_date = end_date.strftime('%Y-%m-%d')
        
        print(f"Fetching price data for {symbol} from {start_date} to {end_date}")
        
        # Fetch 1m data for the trade period
        try:
            df = yf.download(
                tickers=symbol,
                start=start_date,
                end=end_date,
                interval='1m',
                progress=False
            )
        except Exception as e:
            print(f"Error fetching data from yfinance: {str(e)}")
            return jsonify({"error": f"Failed to fetch market data: {str(e)}"}), 500
        
        if df.empty:
            print(f"No data returned for {symbol}")
            return jsonify({"error": f"No price data found for {symbol}"}), 404
        
        # Convert to list of dicts for JSON response
        price_data = []
        for idx, row in df.iterrows():
            price_data.append({
                'timestamp': idx.isoformat(),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume'])
            })
        
        # Prepare response
        response = {
            'trade': {
                'id': trade.id,
                'symbol': trade.symbol,
                'direction': trade.direction,
                'entry_price': float(trade.entry_price),
                'exit_price': float(trade.exit_price),
                'stop_loss': float(trade.stop_loss) if trade.stop_loss else None,
                'take_profit': float(trade.take_profit) if trade.take_profit else None,
                'entry_time': trade.date.isoformat(),
                'exit_time': trade.updated_at.isoformat() if hasattr(trade, 'updated_at') else None,
                'pnl': float(trade.pnl) if trade.pnl else 0.0
            },
            'price_data': price_data
        }
        
        print(f"Successfully generated exit analysis for trade {trade_id}")
        return jsonify(response)
        
    except Exception as e:
        import traceback
        print(f"exit_analysis error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": "An error occurred while processing your request"}), 500

# ─── Exit Analysis Metrics ───────────────────────────────────────────────

@journal_bp.route('/analytics/exit-metrics', methods=['GET'])
@jwt_required()
def exit_metrics_analysis():
    """
    Calculate exit metrics (MAE, MFE) for all trades.
    
    Query Parameters:
        from_date: Filter trades on or after this date (YYYY-MM-DD)
        to_date: Filter trades on or before this date (YYYY-MM-DD)
        symbol: Optional symbol filter
        direction: Optional direction filter (LONG/SHORT)
        
    Returns:
        JSON with exit metrics including MAE, MFE, and other trade statistics
    """
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        
        # Parse query parameters
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        symbols = request.args.get('symbols')
        directions = request.args.get('directions')
        strategies = request.args.get('strategies')
        setups = request.args.get('setups')
        min_pnl = request.args.get('min_pnl')
        max_pnl = request.args.get('max_pnl')
        min_rr = request.args.get('min_rr')
        max_rr = request.args.get('max_rr')
        batch_ids = request.args.get('batch_ids')
        variables_param = request.args.get('variables')
        
        # Base query
        query = JournalEntry.query.filter_by(user_id=user_id, profile_id=profile_id)
        
        # Apply date filters if provided
        if from_date:
            try:
                from_date = datetime.strptime(from_date, '%Y-%m-%d')
                query = query.filter(JournalEntry.date >= from_date)
            except ValueError:
                pass
        if to_date:
            try:
                to_date = datetime.strptime(to_date, '%Y-%m-%d')
                query = query.filter(JournalEntry.date <= to_date)
            except ValueError:
                pass
        
        # Apply symbol filter
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
            if symbol_list:
                query = query.filter(JournalEntry.symbol.in_(symbol_list))
        
        # Apply direction filter
        if directions:
            direction_list = [d.strip() for d in directions.split(',') if d.strip()]
            if direction_list:
                query = query.filter(JournalEntry.direction.in_(direction_list))
        
        # Apply strategy filter
        if strategies:
            strategy_list = [s.strip() for s in strategies.split(',') if s.strip()]
            if strategy_list:
                query = query.filter(JournalEntry.strategy.in_(strategy_list))
        
        # Apply setup filter
        if setups:
            setup_list = [s.strip() for s in setups.split(',') if s.strip()]
            if setup_list:
                query = query.filter(JournalEntry.setup.in_(setup_list))
        
        # Apply P&L range filters
        if min_pnl:
            try:
                min_pnl_val = float(min_pnl)
                query = query.filter(JournalEntry.pnl >= min_pnl_val)
            except ValueError:
                pass
        
        if max_pnl:
            try:
                max_pnl_val = float(max_pnl)
                query = query.filter(JournalEntry.pnl <= max_pnl_val)
            except ValueError:
                pass
        
        # Apply R:R range filters
        if min_rr:
            try:
                min_rr_val = float(min_rr)
                query = query.filter(JournalEntry.rr >= min_rr_val)
            except ValueError:
                pass
        
        if max_rr:
            try:
                max_rr_val = float(max_rr)
                query = query.filter(JournalEntry.rr <= max_rr_val)
            except ValueError:
                pass
        
        # Apply import batch filter
        if batch_ids:
            try:
                batch_id_list = [int(b.strip()) for b in batch_ids.split(',') if b.strip()]
                if batch_id_list:
                    query = query.filter(JournalEntry.import_batch_id.in_(batch_id_list))
            except ValueError:
                pass
        
        # Get filtered trades
        trades = query.all()

        # Apply variables filter if provided
        if variables_param:
            try:
                variables_filter = json.loads(variables_param)
                if isinstance(variables_filter, dict) and variables_filter:
                    trades = [trade for trade in trades if apply_variables_filter(trade, variables_filter)]
            except (json.JSONDecodeError, TypeError):
                # Ignore malformed variables filter
                pass

        
        results = []
        
        for trade in trades:
            if not all([trade.entry_price, trade.exit_price, trade.direction]):
                continue
                
            entry = float(trade.entry_price)
            exit_price = float(trade.exit_price)
            stop_loss = float(trade.stop_loss) if trade.stop_loss else None
            take_profit = float(trade.take_profit) if trade.take_profit else None
            high_price = float(trade.high_price) if hasattr(trade, 'high_price') and trade.high_price else exit_price
            low_price = float(trade.low_price) if hasattr(trade, 'low_price') and trade.low_price else exit_price
            is_long = trade.direction.upper() in ['LONG', 'BUY']
            
            # Calculate P&L percentage
            if is_long:
                pnl_pct = ((exit_price - entry) / entry) * 100
            else:
                pnl_pct = ((entry - exit_price) / entry) * 100
            
            # Calculate Maximum Adverse Excursion (MAE) and Maximum Favorable Excursion (MFE)
            if is_long:
                max_price = max(high_price, exit_price, entry)
                min_price = min(low_price, exit_price, entry)
                mfe = ((max_price - entry) / entry) * 100
                mae = ((min_price - entry) / entry) * 100  # Negative for drawdowns
            else:
                max_price = max(high_price, exit_price, entry)
                min_price = min(low_price, exit_price, entry)
                mfe = ((entry - min_price) / entry) * 100
                mae = ((entry - max_price) / entry) * 100  # Negative for drawdowns
            
            # Check if TP/SL was hit
            hit_tp = False
            hit_sl = False
            
            if is_long:
                if take_profit and exit_price >= take_profit:
                    hit_tp = True
                if stop_loss and exit_price <= stop_loss:
                    hit_sl = True
            else:
                if take_profit and exit_price <= take_profit:
                    hit_tp = True
                if stop_loss and exit_price >= stop_loss:
                    hit_sl = True
            
            results.append({
                'trade_id': trade.id,
                'symbol': trade.symbol,
                'direction': 'LONG' if is_long else 'SHORT',
                'entry_price': entry,
                'exit_price': exit_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'high_price': high_price,
                'low_price': low_price,
                'pnl_pct': pnl_pct,
                'mae': mae,  # Maximum Adverse Excursion (negative for drawdowns)
                'mfe': mfe,  # Maximum Favorable Excursion
                'hit_tp': hit_tp,
                'hit_sl': hit_sl,
                'date': trade.date.isoformat() if trade.date else None,
                'exit_date': trade.updated_at.isoformat() if hasattr(trade, 'updated_at') and trade.updated_at else None
            })
        
        # Calculate aggregated metrics
        total_trades = len(results)
        winning_trades = len([r for r in results if r['pnl_pct'] > 0])
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Calculate average MAE/MFE for winners and losers
        winners_mae = [abs(r['mae']) for r in results if r['pnl_pct'] > 0]
        losers_mae = [abs(r['mae']) for r in results if r['pnl_pct'] <= 0]
        winners_mfe = [r['mfe'] for r in results if r['pnl_pct'] > 0]
        losers_mfe = [r['mfe'] for r in results if r['pnl_pct'] <= 0]
        
        response = {
            'trades': results,
            'summary': {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'avg_mae': sum(abs(r['mae']) for r in results) / total_trades if total_trades > 0 else 0,
                'avg_mfe': sum(r['mfe'] for r in results) / total_trades if total_trades > 0 else 0,
                'avg_winning_mae': sum(winners_mae) / len(winners_mae) if winners_mae else 0,
                'avg_losing_mae': sum(losers_mae) / len(losers_mae) if losers_mae else 0,
                'avg_winning_mfe': sum(winners_mfe) / len(winners_mfe) if winners_mfe else 0,
                'avg_losing_mfe': sum(losers_mfe) / len(losers_mfe) if losers_mfe else 0,
                'hit_tp_count': len([r for r in results if r['hit_tp']]),
                'hit_sl_count': len([r for r in results if r['hit_sl']]),
                'no_tp_sl_count': len([r for r in results if not r['hit_tp'] and not r['hit_sl']])
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        import traceback
        error_msg = f"exit_metrics_analysis error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return jsonify({"error": "An error occurred while processing your request", "details": str(e)}), 500
        return jsonify({"error": "An error occurred while calculating exit metrics"}), 500

# ─── Exit Analysis Summary ───────────────────────────────────────────────────

@journal_bp.route('/exit-analysis-summary', methods=['GET'])
@jwt_required()
def exit_analysis_summary():
    """
    Calculate updraw and drawdown for all trades to be visualized in a summary chart.
    Also calculates summary statistics for the exit analysis.
    """
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        print(f"\n=== Processing exit analysis summary for user {user_id}, profile {profile_id} ===")
        
        timeframe = request.args.get('timeframe', 'all')
        mode = request.args.get('mode', 'average')

        # Build base query
        query = JournalEntry.query.filter_by(user_id=user_id, profile_id=profile_id)
        
        # Apply filters if provided
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        symbols = request.args.get('symbols')
        directions = request.args.get('directions')
        strategies = request.args.get('strategies')
        setups = request.args.get('setups')
        min_pnl = request.args.get('min_pnl')
        max_pnl = request.args.get('max_pnl')
        min_rr = request.args.get('min_rr')
        max_rr = request.args.get('max_rr')
        batch_ids = request.args.get('batch_ids')
        time_of_day = request.args.get('time_of_day')
        day_of_week = request.args.get('day_of_week')
        month = request.args.get('month')
        year = request.args.get('year')
        variables_param = request.args.get('variables')
        
        # Apply date filters
        if from_date:
            query = query.filter(JournalEntry.date >= from_date)
        if to_date:
            query = query.filter(JournalEntry.date <= to_date)
            
        # Apply symbol filter
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(',')]
            query = query.filter(JournalEntry.symbol.in_(symbol_list))
            
        # Apply direction filter
        if directions:
            direction_list = [d.strip() for d in directions.split(',')]
            query = query.filter(JournalEntry.direction.in_(direction_list))
            
        # Apply strategy filter
        if strategies:
            strategy_list = [s.strip() for s in strategies.split(',')]
            query = query.filter(JournalEntry.strategy.in_(strategy_list))
            
        # Apply setup filter
        if setups:
            setup_list = [s.strip() for s in setups.split(',')]
            query = query.filter(JournalEntry.setup.in_(setup_list))
            
        # Apply PnL range filter
        if min_pnl:
            query = query.filter(JournalEntry.pnl >= float(min_pnl))
        if max_pnl:
            query = query.filter(JournalEntry.pnl <= float(max_pnl))
            
        # Apply R:R range filter
        if min_rr:
            query = query.filter(JournalEntry.rr >= float(min_rr))
        if max_rr:
            query = query.filter(JournalEntry.rr <= float(max_rr))
            
        # Apply import batch filter
        if batch_ids:
            batch_list = [int(b.strip()) for b in batch_ids.split(',')]
            query = query.filter(JournalEntry.import_batch_id.in_(batch_list))
            
        # Apply time of day filter
        if time_of_day:
            time_list = [t.strip() for t in time_of_day.split(',')]
            time_conditions = []
            for time_range in time_list:
                if ':' in time_range:
                    start_time, end_time = time_range.split('-')
                    time_conditions.append(
                        JournalEntry.time.between(start_time.strip(), end_time.strip())
                    )
            if time_conditions:
                query = query.filter(or_(*time_conditions))
                
        # Apply day of week filter
        if day_of_week:
            day_list = [d.strip() for d in day_of_week.split(',')]
            day_conditions = []
            for day in day_list:
                day_conditions.append(extract('dow', JournalEntry.date) == day)
            if day_conditions:
                query = query.filter(or_(*day_conditions))
                
        # Apply month filter
        if month:
            month_list = [m.strip() for m in month.split(',')]
            month_conditions = []
            for month_val in month_list:
                month_conditions.append(extract('month', JournalEntry.date) == int(month_val))
            if month_conditions:
                query = query.filter(or_(*month_conditions))
                
        # Apply year filter
        if year:
            year_list = [y.strip() for y in year.split(',')]
            year_conditions = []
            for year_val in year_list:
                year_conditions.append(extract('year', JournalEntry.date) == int(year_val))
            if year_conditions:
                query = query.filter(or_(*year_conditions))

        # Apply timeframe filter (existing logic)
        today = datetime.utcnow().date()
        if timeframe == 'daily':
            query = query.filter(JournalEntry.date >= today)
        elif timeframe == 'weekly':
            start_of_week = today - timedelta(days=today.weekday())
            query = query.filter(JournalEntry.date >= start_of_week)

        # Get filtered entries
        trades = query.order_by(JournalEntry.date.asc()).all()
        print(f"Found {len(trades)} trades for user {user_id} after filtering")
        
        # Apply variables filter if provided
        if variables_param:
            try:
                variables_filter = json.loads(variables_param)
                if isinstance(variables_filter, dict) and variables_filter:
                    trades = [trade for trade in trades if apply_variables_filter(trade, variables_filter)]
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error parsing variables filter: {e}")
                # Continue without variables filter if there's an error

        if not trades:
            return jsonify({"chart_data": [], "summary_stats": {}})

        chart_data = []
        winning_updraws, losing_updraws = [], []
        winning_drawdowns, losing_drawdowns = [], []
        winning_exits, losing_exits = [], []
        hit_tp_count = 0
        hit_sl_count = 0
        processed_trades_count = 0

        for trade in trades:
            try:
                if not all([trade.entry_price is not None, trade.exit_price is not None, trade.direction, trade.pnl is not None]):
                    continue

                entry_price = float(trade.entry_price)
                exit_price = float(trade.exit_price)
                high_price = float(trade.high_price if trade.high_price is not None else max(entry_price, exit_price))
                low_price = float(trade.low_price if trade.low_price is not None else min(entry_price, exit_price))
                take_profit = float(trade.take_profit) if trade.take_profit is not None else None
                stop_loss = float(trade.stop_loss) if trade.stop_loss is not None else None
                direction = trade.direction.lower()
                pnl = float(trade.pnl)
            except (ValueError, TypeError, AttributeError):
                continue

            if entry_price == 0:
                continue
            
            processed_trades_count += 1

            # --- Normalization Logic ---
            # A trade must have TP and SL to be included in this normalized view.
            if take_profit is None or stop_loss is None:
                continue

            # For normalization, the range can't be zero.
            if entry_price == take_profit or entry_price == stop_loss:
                continue

            # Normalize high, low, and exit prices to a scale of -100 (SL) to +100 (TP)
            def normalize(price, entry, tp, sl, is_long):
                if is_long:
                    reward_range = tp - entry
                    risk_range = entry - sl
                    if reward_range <= 0 or risk_range <= 0: return 0 # Invalid SL/TP for a long
                    
                    if price >= entry:
                        return ((price - entry) / reward_range) * 100
                    else:
                        return ((price - entry) / risk_range) * 100
                else: # Short
                    reward_range = entry - tp
                    risk_range = sl - entry
                    if reward_range <= 0 or risk_range <= 0: return 0 # Invalid SL/TP for a short

                    if price <= entry:
                        return ((entry - price) / reward_range) * 100
                    else:
                        return ((entry - price) / risk_range) * 100

            is_long = direction == 'long'
            exit_pct = normalize(exit_price, entry_price, take_profit, stop_loss, is_long)
            high_pct = normalize(high_price, entry_price, take_profit, stop_loss, is_long)
            low_pct = normalize(low_price, entry_price, take_profit, stop_loss, is_long)
            
            # Updraw is the max favorable percentage
            # Drawdown is the max adverse percentage
            if is_long:
                # For long trades, updraw comes from the high, drawdown from the low.
                final_updraw = high_pct
                final_drawdown = low_pct
            else:
                # For short trades, it's inverted: updraw from the low, drawdown from the high.
                final_updraw = low_pct
                final_drawdown = high_pct

            # Ensure updraw is always positive (or zero) and drawdown is always negative (or zero).
            final_updraw = max(0, final_updraw)
            final_drawdown = min(0, final_drawdown)

            exit_pct = min(100, max(-100, exit_pct))

            chart_data.append({
                'trade_id': trade.id,
                'updraw': final_updraw,
                'drawdown': final_drawdown,
                'exit': exit_pct,
                'actual_pnl': pnl,  # Add actual P&L for proper win rate calculation
                'symbol': trade.symbol,
                'direction': trade.direction,
                # Add raw price data for proper RR calculations
                'entry_price': entry_price,
                'exit_price': exit_price,
                'high_price': high_price,
                'low_price': low_price,
                'take_profit': take_profit,
                'stop_loss': stop_loss,
                'original_rr': trade.rr if trade.rr is not None else None
            })

            if pnl > 0:
                winning_updraws.append(final_updraw)
                winning_drawdowns.append(final_drawdown)
                winning_exits.append(exit_pct)
            elif pnl < 0:
                losing_updraws.append(final_updraw)
                losing_drawdowns.append(final_drawdown)
                losing_exits.append(exit_pct)

            if take_profit is not None:
                if (direction == 'long' and high_price >= take_profit) or \
                   (direction == 'short' and low_price <= take_profit):
                    hit_tp_count += 1
            
            if stop_loss is not None:
                if (direction == 'long' and low_price <= stop_loss) or \
                   (direction == 'short' and high_price >= stop_loss):
                    hit_sl_count += 1

        if mode == 'median':
            calc_func = np.median
        else:
            calc_func = np.mean

        summary_stats = {
            'trades_hit_tp': (hit_tp_count / processed_trades_count) * 100 if processed_trades_count > 0 else 0,
            'trades_hit_sl': (hit_sl_count / processed_trades_count) * 100 if processed_trades_count > 0 else 0,
            'avg_updraw_winner': float(calc_func(winning_updraws)) if winning_updraws else 0,
            'avg_updraw_loser': float(calc_func(losing_updraws)) if losing_updraws else 0,
            'avg_drawdown_winner': float(calc_func(winning_drawdowns)) if winning_drawdowns else 0,
            'avg_drawdown_loser': float(calc_func(losing_drawdowns)) if losing_drawdowns else 0,
            'avg_exit_winner': float(calc_func(winning_exits)) if winning_exits else 0,
            'avg_exit_loser': float(calc_func(losing_exits)) if losing_exits else 0,
        }

        return jsonify({
            "chart_data": chart_data,
            "summary_stats": summary_stats
        })
        
    except Exception as e:
        print(f"Error in exit_analysis_summary: {str(e)}")
        return jsonify({'error': str(e)}), 500

@journal_bp.route('/pnl-distribution', methods=['GET'])
@jwt_required()
def pnl_distribution():
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        print(f"\n=== Processing PnL distribution for user {user_id}, profile {profile_id} ===")
        print(f"Request args: {dict(request.args)}")
        
        timeframe = request.args.get('timeframe', 'all').strip()
        print(f"Timeframe: {timeframe}")

        # Build base query
        base_query = build_group_aware_query(user_id, profile_id).filter(JournalEntry.pnl.isnot(None)).filter(JournalEntry.date.isnot(None))
        
        # Apply filters if provided
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        symbols = request.args.get('symbols')
        directions = request.args.get('directions')
        strategies = request.args.get('strategies')
        setups = request.args.get('setups')
        min_pnl = request.args.get('min_pnl')
        max_pnl = request.args.get('max_pnl')
        min_rr = request.args.get('min_rr')
        max_rr = request.args.get('max_rr')
        batch_ids = request.args.get('batch_ids')
        time_of_day = request.args.get('time_of_day')
        day_of_week = request.args.get('day_of_week')
        month = request.args.get('month')
        year = request.args.get('year')
        variables_param = request.args.get('variables')
        
        # Apply date filters
        if from_date:
            base_query = base_query.filter(JournalEntry.date >= from_date)
        if to_date:
            base_query = base_query.filter(JournalEntry.date <= to_date)
            
        # Apply symbol filter
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(',')]
            base_query = base_query.filter(JournalEntry.symbol.in_(symbol_list))
            
        # Apply direction filter
        if directions:
            direction_list = [d.strip() for d in directions.split(',')]
            base_query = base_query.filter(JournalEntry.direction.in_(direction_list))
            
        # Apply strategy filter
        if strategies:
            strategy_list = [s.strip() for s in strategies.split(',')]
            base_query = base_query.filter(JournalEntry.strategy.in_(strategy_list))
            
        # Apply setup filter
        if setups:
            setup_list = [s.strip() for s in setups.split(',')]
            base_query = base_query.filter(JournalEntry.setup.in_(setup_list))
            
        # Apply PnL range filter
        if min_pnl:
            base_query = base_query.filter(JournalEntry.pnl >= float(min_pnl))
        if max_pnl:
            base_query = base_query.filter(JournalEntry.pnl <= float(max_pnl))
            
        # Apply R:R range filter
        if min_rr:
            base_query = base_query.filter(JournalEntry.rr >= float(min_rr))
        if max_rr:
            base_query = base_query.filter(JournalEntry.rr <= float(max_rr))
            
        # Apply import batch filter
        if batch_ids:
            batch_list = [int(b.strip()) for b in batch_ids.split(',')]
            base_query = base_query.filter(JournalEntry.import_batch_id.in_(batch_list))
            
        # Apply time of day filter
        if time_of_day:
            time_list = [t.strip() for t in time_of_day.split(',')]
            time_conditions = []
            for time_range in time_list:
                if ':' in time_range:
                    start_time, end_time = time_range.split('-')
                    time_conditions.append(
                        JournalEntry.time.between(start_time.strip(), end_time.strip())
                    )
            if time_conditions:
                base_query = base_query.filter(or_(*time_conditions))
                
        # Apply day of week filter
        if day_of_week:
            day_list = [d.strip() for d in day_of_week.split(',')]
            day_conditions = []
            for day in day_list:
                day_conditions.append(extract('dow', JournalEntry.date) == day)
            if day_conditions:
                base_query = base_query.filter(or_(*day_conditions))
                
        # Apply month filter
        if month:
            month_list = [m.strip() for m in month.split(',')]
            month_conditions = []
            for month_val in month_list:
                month_conditions.append(extract('month', JournalEntry.date) == int(month_val))
            if month_conditions:
                base_query = base_query.filter(or_(*month_conditions))
                
        # Apply year filter
        if year:
            year_list = [y.strip() for y in year.split(',')]
            year_conditions = []
            for year_val in year_list:
                year_conditions.append(extract('year', JournalEntry.date) == int(year_val))
            if year_conditions:
                base_query = base_query.filter(or_(*year_conditions))


        trades = base_query.all()

        # Apply variables filter if provided
        if variables_param:
            try:
                variables_filter = json.loads(variables_param)
                print(f"Variables filter: {variables_filter}")
                if isinstance(variables_filter, dict) and variables_filter:
                    original_count = len(trades)
                    # Debug: Print first few trades' variables
                    print(f"Sample trades variables:")
                    for i, trade in enumerate(trades[:3]):
                        print(f"  Trade {i}: variables={trade.variables}, extra_data={getattr(trade, 'extra_data', None)}")
                    
                    trades = [trade for trade in trades if apply_variables_filter(trade, variables_filter)]
                    print(f"Applied variables filter: {original_count} -> {len(trades)} trades")
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error parsing variables filter: {e}")
                # Ignore malformed variables filter
                pass

        if timeframe == 'all':
            # Use the already filtered trades, just order them
            trades = sorted(trades, key=lambda x: x.date)
            print(f"Found {len(trades)} trades for user {user_id} after filtering")
            
            if not trades:
                print("No trades found, returning empty data")
                return jsonify({'pnl_data': [], 'average_pnl': 0, 'median_pnl': 0})

            pnl_values = [trade.pnl for trade in trades]
            pnl_data = [{
                'trade_number': i + 1,
                'pnl': trade.pnl,
                'date': trade.date.strftime('%Y-%m-%d'),
                'trade_count': 1
            } for i, trade in enumerate(trades)]
        else:
            if timeframe == 'daily':
                group_format = '%Y-%m-%d'
            elif timeframe == 'weekly':
                group_format = '%Y-%W'
            elif timeframe == 'monthly':
                group_format = '%Y-%m'
            elif timeframe == 'yearly':
                group_format = '%Y'
            else:
                return jsonify({'error': 'Invalid timeframe'}), 400

            # Use the filtered base_query for aggregation
            # Dialect-specific date formatting for cross-database compatibility (SQLite vs PostgreSQL)
            if db.engine.dialect.name == 'postgresql':
                if timeframe == 'daily':
                    period_format = 'YYYY-MM-DD'
                elif timeframe == 'weekly':
                    period_format = 'IYYY-IW' # ISO 8601 week number
                elif timeframe == 'monthly':
                    period_format = 'YYYY-MM'
                else: # yearly
                    period_format = 'YYYY'
                period_func = func.to_char(JournalEntry.date, period_format)
            else: # sqlite
                period_func = func.strftime(group_format, JournalEntry.date)

            aggregated_data = base_query.with_entities(
                period_func.label('period'),
                func.sum(JournalEntry.pnl).label('total_pnl'),
                func.count(JournalEntry.id).label('trade_count')
            ).group_by('period').order_by('period').all()

            print(f"Aggregated data: {aggregated_data}")
            
            if not aggregated_data:
                print("No aggregated data found, returning empty data")
                return jsonify({'pnl_data': [], 'average_pnl': 0, 'median_pnl': 0})

            pnl_values = [item.total_pnl for item in aggregated_data]
            pnl_data = [{'period': item.period, 'pnl': item.total_pnl, 'trade_count': item.trade_count} for item in aggregated_data]
            print(f"Generated pnl_data: {pnl_data}")

        average_pnl = np.mean(pnl_values) if pnl_values else 0
        median_pnl = np.median(pnl_values) if pnl_values else 0

        response_data = {
            'pnl_data': pnl_data,
            'average_pnl': float(average_pnl),
            'median_pnl': float(median_pnl)
        }
        
        print(f"Returning response: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in pnl_distribution: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ─── Streak Analysis ───────────────────────────────────────────────────────
@journal_bp.route('/streaks', methods=['GET'])
@jwt_required()
def streak_analysis():
    """
    Calculate and return streak statistics for the current user's trades.
    
    Returns:
        JSON with streak statistics including current streak, longest winning/losing streaks,
        and distribution of streaks.
    """
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        print(f"\n=== Processing streak analysis for user {user_id}, profile {profile_id} ===")
        
        # Build base query
        query = build_group_aware_query(user_id, profile_id).order_by(JournalEntry.date.asc())
        
        # Apply filters if provided
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        symbols = request.args.get('symbols')
        directions = request.args.get('directions')
        strategies = request.args.get('strategies')
        setups = request.args.get('setups')
        min_pnl = request.args.get('min_pnl')
        max_pnl = request.args.get('max_pnl')
        min_rr = request.args.get('min_rr')
        max_rr = request.args.get('max_rr')
        batch_ids = request.args.get('batch_ids')
        time_of_day = request.args.get('time_of_day')
        day_of_week = request.args.get('day_of_week')
        month = request.args.get('month')
        year = request.args.get('year')
        variables_param = request.args.get('variables')
        
        # Apply date filters
        if from_date:
            query = query.filter(JournalEntry.date >= from_date)
        if to_date:
            query = query.filter(JournalEntry.date <= to_date)
            
        # Apply symbol filter
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(',')]
            query = query.filter(JournalEntry.symbol.in_(symbol_list))
            
        # Apply direction filter
        if directions:
            direction_list = [d.strip() for d in directions.split(',')]
            query = query.filter(JournalEntry.direction.in_(direction_list))
            
        # Apply strategy filter
        if strategies:
            strategy_list = [s.strip() for s in strategies.split(',')]
            query = query.filter(JournalEntry.strategy.in_(strategy_list))
            
        # Apply setup filter
        if setups:
            setup_list = [s.strip() for s in setups.split(',')]
            query = query.filter(JournalEntry.setup.in_(setup_list))
            
        # Apply PnL range filter
        if min_pnl:
            query = query.filter(JournalEntry.pnl >= float(min_pnl))
        if max_pnl:
            query = query.filter(JournalEntry.pnl <= float(max_pnl))
            
        # Apply R:R range filter
        if min_rr:
            query = query.filter(JournalEntry.rr >= float(min_rr))
        if max_rr:
            query = query.filter(JournalEntry.rr <= float(max_rr))
            
        # Apply import batch filter
        if batch_ids:
            batch_list = [int(b.strip()) for b in batch_ids.split(',')]
            query = query.filter(JournalEntry.import_batch_id.in_(batch_list))
            
        # Apply time of day filter
        if time_of_day:
            time_list = [t.strip() for t in time_of_day.split(',')]
            time_conditions = []
            for time_range in time_list:
                if ':' in time_range:
                    start_time, end_time = time_range.split('-')
                    time_conditions.append(
                        JournalEntry.time.between(start_time.strip(), end_time.strip())
                    )
            if time_conditions:
                query = query.filter(or_(*time_conditions))
                
        # Apply day of week filter
        if day_of_week:
            day_list = [d.strip() for d in day_of_week.split(',')]
            day_conditions = []
            for day in day_list:
                day_conditions.append(extract('dow', JournalEntry.date) == day)
            if day_conditions:
                query = query.filter(or_(*day_conditions))
                
        # Apply month filter
        if month:
            month_list = [m.strip() for m in month.split(',')]
            month_conditions = []
            for month_val in month_list:
                month_conditions.append(extract('month', JournalEntry.date) == int(month_val))
            if month_conditions:
                query = query.filter(or_(*month_conditions))
                
        # Apply year filter
        if year:
            year_list = [y.strip() for y in year.split(',')]
            year_conditions = []
            for year_val in year_list:
                year_conditions.append(extract('year', JournalEntry.date) == int(year_val))
            if year_conditions:
                query = query.filter(or_(*year_conditions))
        
        # Get filtered entries
        entries = query.all()
        print(f"Found {len(entries)} trades for user {user_id} after filtering")
        
        # Apply variables filter if provided (post-query filtering)
        if variables_param:
            try:
                variables_filter = json.loads(variables_param)
                if isinstance(variables_filter, dict) and variables_filter:
                    filtered_entries = []
                    for entry in entries:
                        matches_all = True
                        for var_name, var_values in variables_filter.items():
                            if not isinstance(var_values, list) or not var_values:
                                continue
                            
                            entry_vars = entry.variables or {}
                            if isinstance(entry_vars, dict):
                                entry_value = entry_vars.get(var_name)
                                if entry_value:
                                    if isinstance(entry_value, list):
                                        entry_values = [str(v).strip().lower() for v in entry_value if v]
                                    else:
                                        entry_values = [str(entry_value).strip().lower()]
                                else:
                                    extra_data = entry.extra_data or {}
                                    if isinstance(extra_data, dict):
                                        entry_value = extra_data.get(var_name)
                                        if entry_value:
                                            if isinstance(entry_value, list):
                                                entry_values = [str(v).strip().lower() for v in entry_value if v]
                                            else:
                                                entry_values = [str(entry_value).strip().lower()]
                                        else:
                                            entry_values = []
                                    else:
                                        entry_values = []
                            else:
                                entry_values = []
                            
                            filter_values = [str(v).strip().lower() for v in var_values if v]
                            if not any(ev in filter_values for ev in entry_values):
                                matches_all = False
                                break
                        
                        if matches_all:
                            filtered_entries.append(entry)
                    
                    entries = filtered_entries
                    print(f"After variables filtering: {len(entries)} trades")
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error parsing variables filter: {e}")
                # Continue without variables filter if there's an error
        
        if not entries:
            return jsonify({
                'total_trades': 0,
                'winning_trades': 0,
                'win_rate': 0,
                'current_streak': {'type': None, 'count': 0, 'start_date': None, 'end_date': None},
                'longest_winning_streak': {'count': 0, 'pnl': 0, 'start_date': None, 'end_date': None},
                'longest_losing_streak': {'count': 0, 'pnl': 0, 'start_date': None, 'end_date': None},
                'winning_streaks': [],
                'losing_streaks': []
            })
        
        # Initialize streak tracking
        current_streak = {'type': None, 'count': 0, 'start_date': None, 'end_date': None}
        winning_streaks = []
        losing_streaks = []
        
        # Track longest streaks
        longest_winning = {'count': 0, 'pnl': 0, 'start_date': None, 'end_date': None}
        longest_losing = {'count': 0, 'pnl': 0, 'start_date': None, 'end_date': None}
        
        # Counters for win rate
        winning_trades = 0
        valid_trades = 0  # Trades with valid PnL (not None)
        
        for entry in entries:
            if entry.pnl is None:
                continue  # Skip trades with no PnL
                
            valid_trades += 1
            is_win = entry.pnl > 0  # Only consider trades with PnL > 0 as wins
            if is_win:
                winning_trades += 1
            
            # Handle current streak
            if current_streak['type'] is None:
                # Start new streak
                current_streak = {
                    'type': 'winning' if is_win else 'losing',
                    'count': 1,
                    'start_date': entry.date.isoformat(),
                    'end_date': entry.date.isoformat(),
                    'pnl': float(entry.pnl) if entry.pnl else 0.0
                }
            elif (current_streak['type'] == 'winning' and is_win) or \
                 (current_streak['type'] == 'losing' and not is_win):
                # Continue current streak
                current_streak['count'] += 1
                current_streak['end_date'] = entry.date.isoformat()
                current_streak['pnl'] += float(entry.pnl) if entry.pnl else 0.0
            else:
                # End current streak and start new one - only keep streaks with count > 1
                if current_streak['count'] > 1:
                    if current_streak['type'] == 'winning':
                        winning_streaks.append(current_streak)
                        if current_streak['count'] > longest_winning['count']:
                            longest_winning = {
                                'count': current_streak['count'],
                                'pnl': current_streak['pnl'],
                                'start_date': current_streak['start_date'],
                                'end_date': current_streak['end_date']
                            }
                    else:
                        losing_streaks.append(current_streak)
                        if current_streak['count'] > longest_losing['count']:
                            longest_losing = {
                                'count': current_streak['count'],
                                'pnl': current_streak['pnl'],
                                'start_date': current_streak['start_date'],
                                'end_date': current_streak['end_date']
                            }
                
                # Start new streak
                current_streak = {
                    'type': 'winning' if is_win else 'losing',
                    'count': 1,
                    'start_date': entry.date.isoformat(),
                    'end_date': entry.date.isoformat(),
                    'pnl': float(entry.pnl) if entry.pnl else 0.0
                }
        
        # Don't forget to add the last streak if it's longer than 1 trade
        if current_streak['count'] > 1:
            if current_streak['type'] == 'winning':
                winning_streaks.append(current_streak)
                if current_streak['count'] > longest_winning['count']:
                    longest_winning = {
                        'count': current_streak['count'],
                        'pnl': current_streak['pnl'],
                        'start_date': current_streak['start_date'],
                        'end_date': current_streak['end_date']
                    }
            else:
                losing_streaks.append(current_streak)
                if current_streak['count'] > longest_losing['count']:
                    longest_losing = {
                        'count': current_streak['count'],
                        'pnl': current_streak['pnl'],
                        'start_date': current_streak['start_date'],
                        'end_date': current_streak['end_date']
                    }
        
        # Calculate win rate based on valid trades only
        win_rate = round(winning_trades / valid_trades * 100, 2) if valid_trades > 0 else 0
        
        # Prepare the response
        response = {
            'total_trades': len(entries),
            'valid_trades': valid_trades,  # Include count of trades with valid PnL
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'current_streak': {
                'type': current_streak['type'],
                'count': current_streak['count'],
                'start_date': current_streak['start_date'],
                'end_date': current_streak['end_date']
            },
            'longest_winning_streak': longest_winning,
            'longest_losing_streak': longest_losing,
            'winning_streaks': [{
                'count': s['count'],
                'start_date': s['start_date'],
                'end_date': s['end_date'],
                'pnl': s['pnl']
            } for s in winning_streaks],
            'losing_streaks': [{
                'count': s['count'],
                'start_date': s['start_date'],
                'end_date': s['end_date'],
                'pnl': s['pnl']
            } for s in losing_streaks]
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f"Error in streak_analysis: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ─── Equity Analytics ────────────────────────────────────────────────────────
@journal_bp.route('/equities', methods=['GET'])
@jwt_required()
def get_equity_curve():
    """
    Return equity curve data and performance metrics for the current user.
    
    Response format:
    {
        "equity_curve": [
            {"date": "YYYY-MM-DD", "equity": float, "cumulative_pnl": float, "daily_return": float},
            ...
        ],
        "metrics": {
            "sharpe_ratio": float,
            "sortino_ratio": float,
            "max_drawdown": float,
            "max_drawdown_pct": float,
            "total_return": float,
            "annualized_return": float,
            "volatility": float,
            "win_rate": float,
            "profit_factor": float
        },
        "performance_by_period": {
            "daily": [{"date": "YYYY-MM-DD", "pnl": float, "return": float}],
            "weekly": [{"week_start": "YYYY-MM-DD", "pnl": float, "return": float}],
            "monthly": [{"month": "YYYY-MM", "pnl": float, "return": float}]
        }
    }
    """
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        
        # Build base query
        query = build_group_aware_query(user_id, profile_id).order_by(JournalEntry.date.asc())
        
        # Apply filters if provided
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        symbols = request.args.get('symbols')
        directions = request.args.get('directions')
        strategies = request.args.get('strategies')
        setups = request.args.get('setups')
        min_pnl = request.args.get('min_pnl')
        max_pnl = request.args.get('max_pnl')
        min_rr = request.args.get('min_rr')
        max_rr = request.args.get('max_rr')
        batch_ids = request.args.get('batch_ids')
        variables_param = request.args.get('variables')
        
        # Apply date filters
        if from_date:
            try:
                from_date = datetime.strptime(from_date, '%Y-%m-%d')
                query = query.filter(JournalEntry.date >= from_date)
            except ValueError:
                pass
                
        if to_date:
            try:
                to_date = datetime.strptime(to_date, '%Y-%m-%d')
                query = query.filter(JournalEntry.date <= to_date)
            except ValueError:
                pass
        
        # Apply symbol filter
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
            if symbol_list:
                query = query.filter(JournalEntry.symbol.in_(symbol_list))
        
        # Apply direction filter
        if directions:
            direction_list = [d.strip() for d in directions.split(',') if d.strip()]
            if direction_list:
                query = query.filter(JournalEntry.direction.in_(direction_list))
        
        # Apply strategy filter
        if strategies:
            strategy_list = [s.strip() for s in strategies.split(',') if s.strip()]
            if strategy_list:
                query = query.filter(JournalEntry.strategy.in_(strategy_list))
        
        # Apply setup filter
        if setups:
            setup_list = [s.strip() for s in setups.split(',') if s.strip()]
            if setup_list:
                query = query.filter(JournalEntry.setup.in_(setup_list))
        
        # Apply P&L range filters
        if min_pnl:
            try:
                min_pnl_val = float(min_pnl)
                query = query.filter(JournalEntry.pnl >= min_pnl_val)
            except ValueError:
                pass
        
        if max_pnl:
            try:
                max_pnl_val = float(max_pnl)
                query = query.filter(JournalEntry.pnl <= max_pnl_val)
            except ValueError:
                pass
        
        # Apply R:R range filters
        if min_rr:
            try:
                min_rr_val = float(min_rr)
                query = query.filter(JournalEntry.rr >= min_rr_val)
            except ValueError:
                pass
        
        if max_rr:
            try:
                max_rr_val = float(max_rr)
                query = query.filter(JournalEntry.rr <= max_rr_val)
            except ValueError:
                pass
        
        # Apply import batch filter
        if batch_ids:
            try:
                batch_id_list = [int(b.strip()) for b in batch_ids.split(',') if b.strip()]
                if batch_id_list:
                    query = query.filter(JournalEntry.import_batch_id.in_(batch_id_list))
            except ValueError:
                pass
        
        # Get filtered entries
        entries = query.all()
        
        # Apply variables filter if provided (post-query filtering)
        if variables_param:
            try:
                variables_filter = json.loads(variables_param)
                if isinstance(variables_filter, dict) and variables_filter:
                    filtered_entries = []
                    for entry in entries:
                        matches_all = True
                        for var_name, var_values in variables_filter.items():
                            if not isinstance(var_values, list) or not var_values:
                                continue
                            
                            entry_vars = entry.variables or {}
                            if isinstance(entry_vars, dict):
                                entry_value = entry_vars.get(var_name)
                                if entry_value:
                                    if isinstance(entry_value, list):
                                        entry_values = [str(v).strip().lower() for v in entry_value if v]
                                    else:
                                        entry_values = [str(entry_value).strip().lower()]
                                else:
                                    extra_data = entry.extra_data or {}
                                    if isinstance(extra_data, dict):
                                        entry_value = extra_data.get(var_name)
                                        if entry_value:
                                            if isinstance(entry_value, list):
                                                entry_values = [str(v).strip().lower() for v in entry_value if v]
                                            else:
                                                entry_values = [str(entry_value).strip().lower()]
                                        else:
                                            entry_values = []
                                    else:
                                        entry_values = []
                            else:
                                entry_values = []
                            
                            filter_values = [str(v).strip().lower() for v in var_values if v]
                            if not any(ev in filter_values for ev in entry_values):
                                matches_all = False
                                break
                        
                        if matches_all:
                            filtered_entries.append(entry)
                    
                    entries = filtered_entries
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error parsing variables filter: {e}")
                # Continue without variables filter if there's an error
        
        if not entries:
            return jsonify({
                'equity_curve': [],
                'metrics': {},
                'performance_by_period': {'daily': [], 'weekly': [], 'monthly': []}
            })
        
        # Initialize data structures
        equity_curve = []
        daily_returns = []
        daily_pnl = []
        
        # Calculate cumulative P&L and equity curve
        cumulative_pnl = 0.0
        previous_date = None
        
        # First pass: group trades by date
        trades_by_date = {}
        for entry in entries:
            trade_date = entry.date.strftime('%Y-%m-%d') if entry.date else entry.created_at.strftime('%Y-%m-%d')
            if trade_date not in trades_by_date:
                trades_by_date[trade_date] = []
            trades_by_date[trade_date].append(entry)
        
        # Sort dates
        sorted_dates = sorted(trades_by_date.keys())
        
        # Calculate daily returns and build equity curve using user's initial balance
        daily_returns = []
        daily_pnl = []
        equity_curve = []
        
        # Fetch initial balance for proper return calculation
        try:
            eq_user = User.query.get(user_id)
            initial_balance = float(eq_user.initial_balance) if (eq_user and getattr(eq_user, 'initial_balance', 0)) else 0.0
        except Exception:
            initial_balance = 0.0
        
        cumulative_pnl = 0.0
        previous_equity = initial_balance
        for i, date_key in enumerate(sorted_dates):
            # Calculate daily P&L
            daily_total = sum(entry.pnl for entry in trades_by_date[date_key] if entry.pnl is not None)
            
            # Daily return relative to previous equity
            daily_return = (daily_total / previous_equity) if previous_equity else 0.0
            
            cumulative_pnl += daily_total
            current_equity = (initial_balance + cumulative_pnl) if initial_balance else cumulative_pnl
            
            equity_curve.append({
                'date': date_key,
                'equity': current_equity,
                'cumulative_pnl': cumulative_pnl,
                'daily_return': daily_return
            })
            
            daily_returns.append(daily_return)
            daily_pnl.append(daily_total)
            previous_equity = current_equity if initial_balance else (previous_equity + daily_total)
        
        # Calculate performance metrics
        if not daily_returns:
            return jsonify({
                'equity_curve': equity_curve,
                'metrics': {},
                'performance_by_period': {'daily': [], 'weekly': [], 'monthly': []}
            })
        
        import numpy as np
        
        # Calculate metrics
        returns = np.array(daily_returns)
        pnl = np.array(daily_pnl)
        
        # Sharpe Ratio (assuming 0% risk-free rate)
        sharpe_ratio = np.mean(returns) / (np.std(returns) or 1) * np.sqrt(252)  # Annualized
        
        # Sortino Ratio (only downside deviation)
        downside_returns = returns[returns < 0]
        downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0
        
        # Use a minimum threshold to avoid division by zero when all trades have same risk
        min_downside_std = 0.05  # 5% minimum daily downside deviation (more realistic for trading)
        effective_downside_std = max(downside_std, min_downside_std)
        
        if len(downside_returns) > 0:
            # Risk-free rate (assuming 2% annual, converted to daily)
            risk_free_rate_daily = 0.02 / 252
            mean_return = np.mean(returns)
            sortino_raw = ((mean_return - risk_free_rate_daily) / effective_downside_std) * np.sqrt(252)
            
            # Cap the Sortino ratio to realistic values (max 5)
            sortino_ratio = min(sortino_raw, 5.0) if np.isfinite(sortino_raw) else 0.0
        else:
            # No downside risk - perfect scenario
            mean_return = np.mean(returns)
            risk_free_rate_daily = 0.02 / 252
            sortino_ratio = 5.0 if mean_return > risk_free_rate_daily else 0.0  # Cap at 5 instead of infinity
        
        # Max Drawdown
        equity = np.array([e['equity'] for e in equity_curve])
        cummax = np.maximum.accumulate(equity)
        drawdown = (equity - cummax) / (cummax + 1e-10)  # Avoid division by zero
        max_drawdown_pct = abs(min(drawdown)) * 100
        max_drawdown = abs(min(equity - cummax))
        
        # Total return
        total_return = (equity[-1] - equity[0]) / (abs(equity[0]) or 1) * 100 if len(equity) > 1 else 0
        
        # Annualized return (simplified)
        trading_days = len(equity_curve)
        years = trading_days / 252  # Approximate trading days in a year
        annualized_return = ((1 + total_return/100) ** (1/years) - 1) * 100 if years > 0 else 0
        
        # Volatility (annualized)
        volatility = np.std(returns) * np.sqrt(252)
        
        # Win rate and profit factor
        winning_days = sum(1 for r in returns if r > 0)
        win_rate = (winning_days / len(returns)) * 100 if returns.any() else 0
        
        total_gain = sum(r for r in returns if r > 0)
        total_loss = abs(sum(r for r in returns if r < 0))
        profit_factor = total_gain / total_loss if total_loss > 0 else float('inf')
        
        # Group performance by period
        performance_daily = [
            {'date': e['date'], 'pnl': e['cumulative_pnl'] - (equity_curve[i-1]['cumulative_pnl'] if i > 0 else 0), 
             'return': e['daily_return']}
            for i, e in enumerate(equity_curve)
        ]
        
        # Weekly and monthly performance (simplified)
        performance_weekly = []
        performance_monthly = []
        
        # Group by week
        from collections import defaultdict
        weekly_data = defaultdict(list)
        monthly_data = defaultdict(list)
        
        for entry in equity_curve:
            dt = datetime.strptime(entry['date'], '%Y-%m-%d')
            week_start = (dt - timedelta(days=dt.weekday())).strftime('%Y-%m-%d')
            month_start = dt.strftime('%Y-%m-01')
            
            weekly_data[week_start].append(entry)
            monthly_data[month_start].append(entry)
        
        # Calculate weekly performance
        for week_start, week_entries in weekly_data.items():
            if len(week_entries) > 1:
                week_pnl = week_entries[-1]['cumulative_pnl'] - (week_entries[0]['cumulative_pnl'] - week_entries[0]['daily_return'])
                week_return = ((week_entries[-1]['cumulative_pnl'] / (week_entries[0]['cumulative_pnl'] - week_entries[0]['daily_return'])) - 1) * 100 \
                    if (week_entries[0]['cumulative_pnl'] - week_entries[0]['daily_return']) != 0 else 0
                performance_weekly.append({
                    'week_start': week_start,
                    'pnl': week_pnl,
                    'return': week_return
                })
        
        # Calculate monthly performance
        for month_start, month_entries in monthly_data.items():
            if len(month_entries) > 1:
                month_pnl = month_entries[-1]['cumulative_pnl'] - (month_entries[0]['cumulative_pnl'] - month_entries[0]['daily_return'])
                month_return = ((month_entries[-1]['cumulative_pnl'] / (month_entries[0]['cumulative_pnl'] - month_entries[0]['daily_return'])) - 1) * 100 \
                    if (month_entries[0]['cumulative_pnl'] - month_entries[0]['daily_return']) != 0 else 0
                performance_monthly.append({
                    'month': month_start,
                    'pnl': month_pnl,
                    'return': month_return
                })
        
        return jsonify({
            'equity_curve': equity_curve,
            'metrics': {
                'sharpe_ratio': round(float(sharpe_ratio), 2),
                'sortino_ratio': round(float(sortino_ratio), 2),
                'max_drawdown': round(float(max_drawdown), 2),
                'max_drawdown_pct': round(float(max_drawdown_pct), 2),
                'total_return': round(float(total_return), 2),
                'annualized_return': round(float(annualized_return), 2),
                'volatility': round(float(volatility), 2),
                'win_rate': round(float(win_rate), 2),
                'profit_factor': round(float(profit_factor), 2) if profit_factor != float('inf') else None
            },
            'performance_by_period': {
                'daily': performance_daily,
                'weekly': performance_weekly,
                'monthly': performance_monthly
            }
        })
        
    except Exception as e:
        print(f"Error in get_equity_curve: {str(e)}")
        return jsonify({
            'error': 'Failed to calculate equity curve',
            'details': str(e)
        }), 500

# ─── AI Summary ───────────────────────────────────────────────────────────────
@journal_bp.route('/ai-summary', methods=['POST'])
@jwt_required()
def ai_summary():
    if not openai.api_key:
        # Providing a helpful default message if the API key is not set
        return jsonify({'summary': """**AI Assistant is Offline**

To enable the AI-powered review, the site administrator needs to configure the OpenAI API key on the server.

In the meantime, you can continue to use all other features of your trading journal!"""})

    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        stats = data.get('stats')
        language = data.get('language', 'en')

        if not stats or stats.get('total_trades', 0) < 5:
            return jsonify({'summary': "Not enough trade data to generate a meaningful AI review. Keep trading and journaling, and the AI assistant will be ready to help after you've logged at least 5 trades."})

        # We simplify the stats to create a more focused and efficient prompt for the AI.
        prompt_stats = {
            "Total Trades": stats.get('total_trades'),
            "Win Rate (%)": stats.get('win_rate'),
            "Profit Factor": stats.get('profit_factor'),
            "Average R:R": stats.get('avg_rr'),
            "Expectancy ($)": stats.get('expectancy'),
            "Max Drawdown ($)": stats.get('max_drawdown'),
            "Sharpe Ratio": stats.get('sharpe_ratio'),
            "Total P&L ($)": stats.get('total_pnl'),
            "Average Win ($)": stats.get('avg_win'),
            "Average Loss ($)": stats.get('avg_loss'),
            "Max Consecutive Wins": stats.get('max_consecutive_wins'),
            "Max Consecutive Losses": stats.get('max_consecutive_losses'),
        }

        prompt = f"""
You are an expert trading coach providing a review for a trader. Analyze their performance based on these metrics:

{json.dumps(prompt_stats, indent=2)}

Your review should be concise and actionable. Structure your response as follows, using markdown for formatting:
1.  **Overall Assessment:** A one-sentence summary of the trading performance.
2.  **Key Strengths:** 2-3 bullet points on what the trader is doing well.
3.  **Areas for Improvement:** 2-3 bullet points on the main weaknesses.
4.  **Actionable Advice:** 3 concrete suggestions for what to focus on next.

Maintain a supportive and professional tone. Address the trader directly as 'you'.
"""
        if language == 'ar':
            prompt += "\nPlease write the entire review in Arabic."

        # In a real application, you would make a call to the OpenAI API here.
        # For this demonstration, we are returning a detailed, structured mock response.
        # Example API call (uncomment and adapt for production):
        # response = openai.ChatCompletion.create(
        #     model="gpt-4-turbo",
        #     messages=[
        #         {"role": "system", "content": "You are an expert trading coach."},
        #         {"role": "user", "content": prompt}
        #     ],
        #     temperature=0.7,
        #     max_tokens=500
        # )
        # summary = response.choices[0].message['content'].strip()

        # Mocked responses for demonstration purposes:
        if language == 'ar':
            summary = f"""**تقييم عام:**
يُظهر أداؤك أساسًا متينًا مع استراتيجية مربحة, ولكن هناك إمكانية واضحة لتعزيز الاتساق وإدارة المخاطر بشكل أكثر فعالية.

**نقاط القوة الرئيسية:**
*   **الربحية:** استراتيجيتك مربحة بشكل أساسي, ويتضح ذلك من خلال إجمالي ربح وخسارة إيجابي قدره ${stats.get('total_pnl', 0):.2f} وتوقع صحي.
*   **جودة الصفقات الرابحة:** أنت تتفوق في ترك صفقاتك الرابحة تستمر, حيث أن متوسط ربحك (${stats.get('avg_win', 0):.2f}) أكبر بكثير من متوسط خسارتك (${stats.get('avg_loss', 0):.2f}). هذه سمة مميزة للتداول الناجح.

**مجالات للتحسين:**
*   **معدل الربح:** يمكن تحسين معدل ربح بنسبة {stats.get('win_rate', 0)}%. قد يشير هذا إلى أنك تدخل الصفقات قبل الأوان أو تختار صفقات ذات احتمالية أقل.
*   **إدارة التراجع:** يشير أقصى تراجع لديك والبالغ ${stats.get('max_drawdown', 0):.2f} إلى أنك قد تخاطر كثيرًا في صفقات معينة, مما قد يؤثر على نمو رأس مالك على المدى الطويل.

**نصائح قابلة للتنفيذ:**
1.  **صقل معايير الدخول الخاصة بك:** قبل الدخول في صفقة, اسأل نفسك عما إذا كانت تلبي جميع معايير الإعداد المثالي لديك. كن أكثر انتقائية لزيادة معدل ربحك بشكل طبيعي.
2.  **توحيد المخاطر الخاصة بك:** قم بتنفيذ استراتيجية متسقة لتحديد حجم المركز. على سبيل المثال, لا تخاطر بأكثر من 1٪ من رأس مال التداول الخاص بك في أي صفقة واحدة للحفاظ على التراجعات تحت السيطرة.
3.  **حلل صفقاتك الخاسرة:** استخدم دفتر يومياتك للعثور على مواضيع مشتركة بين خسائرك. هل تحدث في وقت معين من اليوم؟ في حالة سوق معينة؟ استخدم هذه الرؤية لتجنب تكرار الأخطاء.

واصل الجهد المنضبط. أنت على الطريق الصحيح لتحقيق أهدافك في التداول!"""
        else:
            summary = f"""**Overall Assessment:**
Your performance shows a solid foundation with a profitable strategy, but there's clear potential to enhance consistency and manage risk more effectively.

**Key Strengths:**
*   **Profitability:** Your strategy is fundamentally profitable, as evidenced by a positive total P&L of ${stats.get('total_pnl', 0):.2f} and a healthy expectancy.
*   **Winning Trade Quality:** You excel at letting your winning trades run, with an average win (${stats.get('avg_win', 0):.2f}) significantly larger than your average loss (${stats.get('avg_loss', 0):.2f}). This is a hallmark of successful trading.

**Areas for Improvement:**
*   **Win Rate:** Your win rate of {stats.get('win_rate', 0)}% can be improved. This might indicate that you're entering trades too early or choosing trades with lower probability.
*   **Drawdown Management:** Your maximum drawdown of ${stats.get('max_drawdown', 0):.2f} suggests that you might be risking too much in certain trades, which could impact your capital growth over time.

**Actionable Advice:**
1.  **Refine Your Entry Criteria:** Before entering a trade, ask yourself if it meets all your ideal setup criteria. Be more selective to naturally increase your win rate.
2.  **Unify Your Risk Management:** Implement a consistent strategy for position sizing. For example, never risk more than 1% of your trading capital in any single trade to keep drawdowns under control.
3.  **Analyze Your Losing Trades:** Use your journal to find common themes among your losses. Do they happen at a specific time of day? In a particular market condition? Use this insight to avoid repeating mistakes.

Keep up the disciplined effort. You're on the right path to achieving your trading goals!"""

        return jsonify({'summary': summary})

    except Exception as e:
        print(f"[AI-SUMMARY-ERROR] {e}")
        return jsonify({'error': 'An unexpected error occurred while generating the AI summary.'}), 500


# ─── Shared import parser ────────────────────────────────────────────────────
def parse_trades_dataframe(df):
    """Parse a pandas DataFrame into a list[dict] trade objects.
    We attempt to map common broker column names to our internal fields.
    Unknown columns are stored in `extra_data` or as variables.
    """
    # Make a copy to avoid modifying the original
    df = df.copy()
    
    # Store original column names for reference
    original_headers = {col.lower(): col for col in df.columns}
    
    # Normalise headers (strip, lower) for processing
    df.columns = [c.strip().lower() for c in df.columns]

    # Heuristic mapping - only for core fields that we need to identify
    core_fields = {
        'symbol': ['symbol', 'pair', 'instrument'],
        'direction': ['type', 'side', 'direction'],
        'entry_price': ['entry price', 'open', 'open price', 'price open'],
        'exit_price': ['exit price', 'close', 'close price', 'price close'],
        'high_price': ['high', 'high price', 'max price', 'price high'],
        'low_price': ['low', 'low price', 'min price', 'price low'],
        'quantity': ['volume', 'qty', 'size', 'lots', 'quantity'],
        'date': ['date', 'open time', 'entry time', 'datetime', 'trade time', 'close time'],
        'time': ['time', 'entry time', 'close time', 'hour', 'trade time'],
        'pnl': ['pnl', 'profit', 'net profit', 'p&l'],
        'rr': ['rr', 'r:r', 'riskreward', 'risk reward', 'risk/reward'],
    }
    
    # Fields that should be excluded from variables
    excluded_from_vars = set()
    for field, aliases in core_fields.items():
        excluded_from_vars.update(aliases)
    excluded_from_vars.update(['id', 'notes', 'tags', 'variables', 'extra_data', 'created_at', 'updated_at'])

    # Build reverse lookup for core fields
    reverse_lookup = {}
    for k, aliases in core_fields.items():
        for alias in aliases:
            reverse_lookup[alias] = k

    # Try to automatically detect date/time columns
    date_columns = []
    time_columns = []
    datetime_columns = []
    
    for col in df.columns:
        col_lower = col.lower()
        if any(x in col_lower for x in ['date', 'time', 'datetime']):
            # Check if column contains datetime strings
            sample = df[col].dropna().head(10).astype(str)
            if sample.empty:
                continue
                
            # Check for datetime format (e.g., '2023-01-01 14:30:00')
            if sample.str.match(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}[T\s]\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:[+-]\d{2}:?\d{2}|Z)?').any():
                datetime_columns.append(col)
            # Check for date format (e.g., '2023-01-01')
            elif sample.str.match(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}').any():
                date_columns.append(col)
            # Check for time format (e.g., '14:30:00')
            elif sample.str.match(r'\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?').any():
                time_columns.append(col)

    trades = []
    for _, row in df.iterrows():
        trade = {
            'symbol': None,
            'direction': None,
            'entry_price': None,
            'exit_price': None,
            'high_price': None,
            'low_price': None,
            'quantity': 1.0,
            'date': None,
            'time': None,
            'datetime': None,
            'pnl': None,
            'rr': None,
            'extra_data': {},
            'variables': {}
        }
        
        # Map known columns and collect variables
        for col in df.columns:
            if pd.isna(row[col]) or row[col] == '':
                continue
                
            col_lower = col.lower()
            
            # Check if this is a core field
            if col_lower in reverse_lookup:
                field = reverse_lookup[col_lower]
                trade[field] = row[col]
            # Only include non-core, non-excluded fields as variables
            elif col_lower not in excluded_from_vars:
                # Use the original column name from the import file and convert to lowercase
                original_col = original_headers.get(col, col).lower()
                # Convert the value to lowercase if it's a string, or process lists of strings
                if isinstance(row[col], str):
                    trade['variables'][original_col] = row[col].lower() if pd.notna(row[col]) and str(row[col]).strip() else row[col]
                elif isinstance(row[col], list):
                    # Handle lists of strings
                    trade['variables'][original_col] = [
                        str(item).lower().strip() 
                        for item in row[col] 
                        if pd.notna(item) and str(item).strip()
                    ]
                else:
                    trade['variables'][original_col] = row[col]
            else:
                # Store in extra_data
                trade['extra_data'][col] = row[col]
        
        # Handle date/time parsing
        if 'datetime' not in trade or not trade['datetime']:
            # Try to combine separate date and time columns
            date_val = trade.get('date')
            time_val = trade.get('time')
            
            if date_val and time_val:
                try:
                    # Convert to string in case they're pandas Timestamp objects
                    date_str = str(date_val).strip()
                    time_str = str(time_val).strip()
                    
                    # Handle different date formats
                    if 'T' in date_str:  # ISO format
                        trade['datetime'] = date_str
                    else:
                        # Combine date and time
                        trade['datetime'] = f"{date_str} {time_str}"
                except Exception as e:
                    print(f"Error combining date and time: {e}")
                    trade['datetime'] = str(date_val)
        
        # If we still don't have a datetime, try to parse the date
        if 'datetime' not in trade or not trade['datetime']:
            if 'date' in trade and trade['date']:
                trade['datetime'] = str(trade['date'])
        
        # Clean up the trade dictionary
        if 'date' in trade and not trade['date']:
            del trade['date']
        if 'time' in trade and not trade['time']:
            del trade['time']
            
        trades.append(trade)
    
    return trades

# ─── Import preview endpoint ────────────────────────────────────────────────
@journal_bp.route('/import/preview', methods=['POST'])
@jwt_required()
def import_preview():
    """Upload a CSV or Excel file & return the first 20 parsed trades for preview."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file field'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    try:
        # Read into pandas depending on extension
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)

        preview_df = df.head(20)
        trades = parse_trades_dataframe(preview_df)
        # Replace NaN with None for JSON serialization
        sanitized_df = preview_df.where(pd.notnull(preview_df), None)
        raw_rows = sanitized_df.to_dict(orient='records')

        import numpy as np
        # Helper to sanitize any NaN/inf values in arbitrary structures
        def _sanitize(value):
            # Replace all NaN/Inf or numpy.nan with None so JSON is valid
            if value is None:
                return None
            if isinstance(value,(float,int)):
                if isinstance(value,float):
                    if np.isnan(value) or np.isinf(value):
                        return None
                return value
            if isinstance(value,np.number):
                if np.isnan(value) or np.isinf(value):
                    return None
                return value.item()
            if isinstance(value, (list, tuple, set)):
                return [_sanitize(v) for v in value]
            if isinstance(value, dict):
                return {k:_sanitize(v) for k,v in value.items()}
            return value

        trades = [_sanitize(t) for t in trades]
        # Basic duplicate detection within preview (same symbol+date+direction+entry)
        seen = set()
        for t in trades:
            key = (t.get('symbol'), t.get('direction'), t.get('entry_price'), t.get('date'))
            if key in seen:
                t['duplicate'] = True
            else:
                t['duplicate'] = False
                seen.add(key)
        payload = _sanitize({'trades': trades, 'raw_rows': raw_rows, 'columns': list(df.columns)})
        import json
        return Response(json.dumps(payload, allow_nan=False), mimetype='application/json')

    except Exception as e:
        print(' import_preview error:', e)
        return jsonify({'error': str(e)}), 500

@journal_bp.route('/variable-breakdown', methods=['GET'])
@jwt_required()
def variable_breakdown():
    """
    Return performance metrics grouped by values of a specific variable key.
    
    Query Parameters:
        key (str): The variable key to group by (e.g., 'var1', 'var2', etc.)
        from_date (str, optional): Filter trades on or after this date (YYYY-MM-DD)
        to_date (str, optional): Filter trades on or before this date (YYYY-MM-DD)
        timeframe (str, optional): Filter trades by timeframe ('all', 'month', 'year')
        
    Returns:
        JSON response with performance metrics grouped by variable values
    """
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        variable_key = request.args.get('key', 'var1')  # Default to 'var1' if not specified
        
        # Get date filters
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        timeframe = request.args.get('timeframe', 'all')
        
        # Base query
        query = build_group_aware_query(user_id, profile_id)
        
        # Apply date filters
        if from_date:
            try:
                from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
                query = query.filter(JournalEntry.date >= from_date)
            except ValueError:
                return jsonify({'error': 'Invalid from_date format. Use YYYY-MM-DD'}), 400
                
        if to_date:
            try:
                to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
                query = query.filter(JournalEntry.date <= to_date)
            except ValueError:
                return jsonify({'error': 'Invalid to_date format. Use YYYY-MM-DD'}), 400
                
        # Apply timeframe filter
        if timeframe != 'all':
            today = date.today()
            if timeframe == 'month':
                first_day = today.replace(day=1)
                query = query.filter(JournalEntry.date >= first_day)
            elif timeframe == 'year':
                first_day = today.replace(month=1, day=1)
                query = query.filter(JournalEntry.date >= first_day)
        
        # Get all trades
        entries = query.all()
        
        # Group trades by variable value
        variable_stats = {}
        
        for entry in entries:
            if not entry.variables or variable_key not in entry.variables:
                continue
                
            value = str(entry.variables[variable_key])
            if not value:  # Skip empty values
                continue
                
            if value not in variable_stats:
                variable_stats[value] = {
                    'trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'total_rr': 0.0,
                    'total_pnl': 0.0,
                    'gross_profit': 0.0,
                    'gross_loss': 0.0,
                    'first_date': None,
                    'last_date': None,
                    'win_amounts': [],
                    'loss_amounts': [],
                    'pnl_history': [],
                    'running_pnl': 0.0,
                    'peak': 0.0,
                    'max_drawdown': 0.0
                }
            
            stats = variable_stats[value]
            stats['trades'] += 1
            
            # Track dates
            if entry.date:
                if stats['first_date'] is None or entry.date < stats['first_date']:
                    stats['first_date'] = entry.date
                if stats['last_date'] is None or entry.date > stats['last_date']:
                    stats['last_date'] = entry.date
            
            # Skip trades with no PnL for calculations
            if entry.pnl is None:
                continue
                
            # Track PnL and RR
            stats['total_pnl'] += entry.pnl
            stats['running_pnl'] += entry.pnl
            if entry.rr:
                stats['total_rr'] += entry.rr
            
            # Track PnL history for drawdown calculation
            stats['pnl_history'].append({
                'date': entry.date.isoformat() if entry.date else None,
                'pnl': entry.pnl or 0.0,
                'cumulative': stats['running_pnl']
            })
            
            # Update peak and drawdown
            if stats['running_pnl'] > stats['peak']:
                stats['peak'] = stats['running_pnl']
            else:
                drawdown = stats['peak'] - stats['running_pnl']
                if drawdown > stats['max_drawdown']:
                    stats['max_drawdown'] = drawdown
            
            # Track wins/losses and amounts
            if entry.pnl > 0:
                stats['wins'] += 1
                stats['gross_profit'] += entry.pnl
                stats['win_amounts'].append(entry.pnl)
            else:
                stats['losses'] += 1
                loss = abs(entry.pnl)
                stats['gross_loss'] += loss
                stats['loss_amounts'].append(loss)
        
        # Calculate metrics for each variable value
        result = []
        best_metric = {'value': None, 'metric': 'profit_factor', 'variable': None}
        total_trades = 0
        total_pnl = 0.0
        total_win_rate = 0.0
        total_profit_factor = 0.0
        variable_count = 0
        
        for value, data in variable_stats.items():
            wins = data['wins']
            losses = data['losses']
            total = data['trades']
            
            if total == 0:
                continue
                
            # Calculate basic metrics
            win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0
            avg_rr = data['total_rr'] / total if total > 0 else 0.0
            
            # Calculate profit factor
            profit_factor = None
            if data['gross_loss'] > 0:
                profit_factor = data['gross_profit'] / data['gross_loss']
            elif data['gross_profit'] > 0:
                profit_factor = float('inf')
            
            # Calculate average win/loss
            avg_win = sum(data['win_amounts']) / len(data['win_amounts']) if data['win_amounts'] else 0.0
            avg_loss = sum(data['loss_amounts']) / len(data['loss_amounts']) if data['loss_amounts'] else 0.0
            
            # Calculate max win/loss
            max_win = max(data['win_amounts'], default=0.0)
            max_loss = max(data['loss_amounts'], default=0.0)
            
            # Calculate expectancy
            win_prob = wins / total if total > 0 else 0
            loss_prob = losses / total if total > 0 else 0
            expectancy = (win_prob * avg_win) - (loss_prob * avg_loss)
            
            # Calculate consistency score (0-1, higher is more consistent)
            consistency = 0.0
            if wins > 0 and losses > 0:
                win_std = (sum((x - avg_win) ** 2 for x in data['win_amounts']) / len(data['win_amounts'])) ** 0.5 if data['win_amounts'] else 0
                loss_std = (sum((x - avg_loss) ** 2 for x in data['loss_amounts']) / len(data['loss_amounts'])) ** 0.5 if data['loss_amounts'] else 0
                consistency = 1 / (1 + (win_std / avg_win if avg_win != 0 else 0) + (loss_std / avg_loss if avg_loss != 0 else 0))
            
            # Sort PnL history by date
            sorted_pnl = sorted(data['pnl_history'], key=lambda x: x['date'] or '')
            
            # Prepare cumulative PnL data for charting
            cumulative_pnl = []
            running_total = 0.0
            for trade in sorted_pnl:
                running_total += trade['pnl']
                cumulative_pnl.append({
                    'date': trade['date'],
                    'value': round(running_total, 2)
                })
            
            # Create stats object for this variable value
            value_stats = {
                'value': value,
                'trades': total,
                'wins': wins,
                'losses': losses,
                'win_rate': round(win_rate, 1),
                'avg_rr': round(avg_rr, 2),
                'pnl': round(data['total_pnl'], 2),
                'profit_factor': round(profit_factor, 2) if profit_factor is not None and profit_factor != float('inf') else None,
                'gross_profit': round(data['gross_profit'], 2),
                'gross_loss': round(data['gross_loss'], 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'max_win': round(max_win, 2),
                'max_loss': round(-max_loss, 2) if max_loss != 0 else 0.0,
                'max_drawdown': round(abs(data['max_drawdown']), 2) if data['max_drawdown'] is not None else 0.0,
                'expectancy': round(expectancy, 2),
                'consistency_score': round(consistency, 2),
                'cumulative_pnl': cumulative_pnl,
                'first_trade_date': data['first_date'].strftime('%Y-%m-%d') if data['first_date'] else None,
                'latest_date': data['last_date'].strftime('%Y-%m-%d') if data['last_date'] else None
            }
            
            # Track best performing variable by profit factor
            if profit_factor is not None and (best_metric['value'] is None or profit_factor > best_metric['value']):
                best_metric = {
                    'value': profit_factor,
                    'metric': 'profit_factor',
                    'variable': value
                }
            
            # Update summary stats
            total_trades += total
            total_pnl += data['total_pnl']
            total_win_rate += win_rate
            if profit_factor is not None and profit_factor != float('inf'):
                total_profit_factor += profit_factor
            variable_count += 1
            
            result.append(value_stats)
        
        # Calculate averages for summary
        avg_win_rate = total_win_rate / variable_count if variable_count > 0 else 0
        avg_profit_factor = total_profit_factor / variable_count if variable_count > 0 else 0
        
        # Sort results by total trades (descending)
        result.sort(key=lambda x: x['trades'], reverse=True)
        
        # Prepare final response
        response = {
            'variable_key': variable_key,
            'values': result,
            'best_performing': best_metric,
            'stats_summary': {
                'total_trades': total_trades,
                'total_pnl': round(total_pnl, 2),
                'avg_win_rate': round(avg_win_rate, 1),
                'avg_profit_factor': round(avg_profit_factor, 2)
            }
        }

        return jsonify(response), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def apply_variables_filter(trade, variables_filter):
    """
    Apply variables filter to a trade with improved logic that handles lists, extra_data, and proper string matching.
    
    Args:
        trade: JournalEntry object
        variables_filter: dict with variable names as keys and lists of values as values
    
    Returns:
        bool: True if trade matches all variable filters, False otherwise
    """
    for var_name, var_values in variables_filter.items():
        if not isinstance(var_values, list) or not var_values:
            continue
        
        # Check variables field first
        entry_vars = trade.variables or {}
        if isinstance(entry_vars, dict):
            entry_value = entry_vars.get(var_name)
            if entry_value:
                if isinstance(entry_value, list):
                    entry_values = [str(v).strip().lower() for v in entry_value if v]
                else:
                    entry_values = [str(entry_value).strip().lower()]
            else:
                # Check extra_data field
                extra_data = getattr(trade, 'extra_data', None) or {}
                if isinstance(extra_data, dict):
                    entry_value = extra_data.get(var_name)
                    if entry_value:
                        if isinstance(entry_value, list):
                            entry_values = [str(v).strip().lower() for v in entry_value if v]
                        else:
                            entry_values = [str(entry_value).strip().lower()]
                    else:
                        entry_values = []
                else:
                    entry_values = []
        else:
            entry_values = []
        
        # Check if any of the entry values match the filter values
        filter_values = [str(v).strip().lower() for v in var_values if v]
        
        # Debug logging
        print(f"Variable filter check: {var_name}")
        print(f"  Trade variables: {trade.variables}")
        print(f"  Trade extra_data: {getattr(trade, 'extra_data', None)}")
        print(f"  Entry values: {entry_values}")
        print(f"  Filter values: {filter_values}")
        print(f"  Match: {any(ev in filter_values for ev in entry_values)}")
        
        if not any(ev in filter_values for ev in entry_values):
            return False
    
    return True

@journal_bp.route('/ai-dashboard', methods=['GET'])
@jwt_required()
def ai_dashboard():
    """AI-powered dashboard with intelligent insights and recommendations"""
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        timeframe = request.args.get('timeframe', '30d')
        
        # Calculate date range
        end_date = datetime.utcnow()
        if timeframe == '7d':
            start_date = end_date - timedelta(days=7)
        elif timeframe == '30d':
            start_date = end_date - timedelta(days=30)
        elif timeframe == '90d':
            start_date = end_date - timedelta(days=90)
        elif timeframe == '1y':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = datetime(2020, 1, 1)  # All time
        
        # Get trades for analysis using group-aware query
        base_query = build_group_aware_query(user_id, profile_id)
        trades = base_query.filter(
            JournalEntry.date >= start_date,
            JournalEntry.date <= end_date
        ).order_by(JournalEntry.date.asc()).all()
        
        if not trades:
            return jsonify({
                'confidenceScore': 0,
                'riskLevel': 'Unknown',
                'riskDescription': 'No trades found for analysis',
                'improvementPotential': 0,
                'nextBestSetup': 'N/A',
                'setupConfidence': 0,
                'performanceInsights': [],
                'riskAnalysis': [],
                'behavioralPatterns': [],
                'recommendations': [],
                'optimalTimes': []
            })
        
        # Calculate basic metrics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl < 0]
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        total_pnl = sum(t.pnl for t in trades)
        avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        # Calculate risk metrics
        max_drawdown = calculate_max_drawdown(trades)
        sharpe_ratio = calculate_sharpe_ratio(trades) if len(trades) > 1 else 0
        
        # AI Confidence Score (based on data quality and consistency)
        confidence_score = min(95, max(10, 
            (total_trades * 2) +  # More trades = higher confidence
            (win_rate * 0.3) +    # Better performance = higher confidence
            (abs(sharpe_ratio) * 5) +  # Better risk-adjusted returns
            (min(total_trades / 10, 20))  # Cap at 20 for sample size
        ))
        
        # Risk Level Assessment
        risk_level, risk_description = assess_risk_level(trades, max_drawdown, sharpe_ratio)
        
        # Performance Insights
        performance_insights = generate_performance_insights(trades, win_rate, avg_win, avg_loss)
        
        # Risk Analysis
        risk_analysis = generate_risk_analysis(trades, max_drawdown, sharpe_ratio)
        
        # Behavioral Patterns
        behavioral_patterns = analyze_behavioral_patterns(trades)
        
        # AI Recommendations
        recommendations = generate_recommendations(trades, win_rate, avg_win, avg_loss, max_drawdown)
        
        # Optimal Trading Times
        optimal_times = analyze_optimal_times(trades)
        
        # Improvement Potential
        improvement_potential = calculate_improvement_potential(trades, win_rate, avg_win, avg_loss)
        
        # Next Best Setup
        next_best_setup, setup_confidence = predict_next_best_setup(trades)
        
        return jsonify({
            'confidenceScore': round(confidence_score, 1),
            'riskLevel': risk_level,
            'riskDescription': risk_description,
            'improvementPotential': round(improvement_potential, 1),
            'nextBestSetup': next_best_setup,
            'setupConfidence': round(setup_confidence, 1),
            'performanceInsights': performance_insights,
            'riskAnalysis': risk_analysis,
            'behavioralPatterns': behavioral_patterns,
            'recommendations': recommendations,
            'optimalTimes': optimal_times
        })
        
    except Exception as e:
        print("AI dashboard error:", e)
        return jsonify({'error': str(e)}), 500

def calculate_max_drawdown(trades):
    """Calculate maximum drawdown from peak"""
    if not trades:
        return 0
    
    cumulative_pnl = 0
    peak = 0
    max_dd = 0
    
    for trade in trades:
        cumulative_pnl += trade.pnl
        if cumulative_pnl > peak:
            peak = cumulative_pnl
        drawdown = (peak - cumulative_pnl) / peak * 100 if peak > 0 else 0
        max_dd = max(max_dd, drawdown)
    
    return max_dd

def calculate_sharpe_ratio(trades):
    """Calculate Sharpe ratio (simplified)"""
    if len(trades) < 2:
        return 0
    
    returns = [t.pnl for t in trades]
    avg_return = sum(returns) / len(returns)
    std_dev = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
    
    return avg_return / std_dev if std_dev > 0 else 0

def assess_risk_level(trades, max_drawdown, sharpe_ratio):
    """Assess overall risk level"""
    if max_drawdown > 20:
        return "High", "Significant drawdown detected. Consider reducing position sizes."
    elif max_drawdown > 10:
        return "Medium", "Moderate risk level. Monitor drawdown closely."
    elif sharpe_ratio < 0.5:
        return "Medium", "Low risk-adjusted returns. Focus on improving win rate."
    else:
        return "Low", "Good risk management. Continue current approach."

def generate_performance_insights(trades, win_rate, avg_win, avg_loss):
    """Generate performance insights"""
    insights = []
    
    # Win rate analysis
    if win_rate < 40:
        insights.append({
            'type': 'negative',
            'title': 'Low Win Rate',
            'description': f'Your win rate is {win_rate:.1f}%, which is below optimal levels.',
            'recommendation': 'Focus on improving entry quality and risk management.'
        })
    elif win_rate > 60:
        insights.append({
            'type': 'positive',
            'title': 'Strong Win Rate',
            'description': f'Excellent win rate of {win_rate:.1f}%.',
            'recommendation': 'Consider increasing position sizes gradually.'
        })
    
    # Risk-reward analysis
    if avg_loss != 0:
        rr_ratio = abs(avg_win / avg_loss)
        if rr_ratio < 1.5:
            insights.append({
                'type': 'negative',
                'title': 'Poor Risk-Reward',
                'description': f'Your average win is {rr_ratio:.1f}x your average loss.',
                'recommendation': 'Aim for at least 2:1 risk-reward ratio.'
            })
        elif rr_ratio > 3:
            insights.append({
                'type': 'positive',
                'title': 'Excellent Risk-Reward',
                'description': f'Great risk-reward ratio of {rr_ratio:.1f}:1.',
                'recommendation': 'Your exit strategy is working well.'
            })
    
    # Consistency analysis
    if len(trades) >= 10:
        recent_trades = trades[-10:]
        recent_win_rate = len([t for t in recent_trades if t.pnl > 0]) / len(recent_trades) * 100
        
        if abs(recent_win_rate - win_rate) > 20:
            insights.append({
                'type': 'neutral',
                'title': 'Inconsistent Performance',
                'description': 'Recent performance differs significantly from overall average.',
                'recommendation': 'Review recent trades for pattern changes.'
            })
    
    return insights

def generate_risk_analysis(trades, max_drawdown, sharpe_ratio):
    """Generate risk analysis"""
    analysis = []
    
    # Drawdown risk
    if max_drawdown > 15:
        analysis.append({
            'title': 'High Drawdown Risk',
            'description': f'Maximum drawdown of {max_drawdown:.1f}% detected.',
            'action': 'Reduce position sizes and implement stricter stop losses.',
            'severity': 'negative',
            'probability': min(90, max_drawdown * 3)
        })
    
    # Volatility risk
    if len(trades) >= 5:
        pnl_values = [t.pnl for t in trades]
        volatility = (sum((pnl - sum(pnl_values)/len(pnl_values)) ** 2 for pnl in pnl_values) / len(pnl_values)) ** 0.5
        
        if volatility > abs(sum(pnl_values) / len(pnl_values)) * 2:
            analysis.append({
                'title': 'High Volatility',
                'description': 'Trade outcomes are highly variable.',
                'action': 'Standardize position sizing and entry criteria.',
                'severity': 'negative',
                'probability': 70
            })
    
    # Concentration risk
    symbols = [t.symbol for t in trades]
    symbol_counts = {}
    for symbol in symbols:
        symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
    
    max_symbol_pct = max(symbol_counts.values()) / len(trades) * 100 if symbol_counts else 0
    if max_symbol_pct > 30:
        analysis.append({
            'title': 'Symbol Concentration',
            'description': f'{max_symbol_pct:.1f}% of trades are in one symbol.',
            'action': 'Diversify across more symbols to reduce risk.',
            'severity': 'negative',
            'probability': 60
        })
    
    return analysis

def analyze_behavioral_patterns(trades):
    """Analyze behavioral patterns"""
    patterns = []
    
    if len(trades) < 5:
        return patterns
    
    # Revenge trading pattern
    consecutive_losses = 0
    max_consecutive_losses = 0
    for trade in trades:
        if trade.pnl < 0:
            consecutive_losses += 1
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        else:
            consecutive_losses = 0
    
    if max_consecutive_losses >= 3:
        patterns.append({
            'name': 'Revenge Trading',
            'description': 'Tendency to increase risk after losses.',
            'impact': 'negative',
            'frequency': min(100, max_consecutive_losses * 20),
            'impactScore': 8
        })
    
    # Overtrading pattern
    if len(trades) > 20:  # Assuming 20+ trades in timeframe indicates overtrading
        avg_trades_per_day = len(trades) / 30  # Assuming 30-day timeframe
        if avg_trades_per_day > 1:
            patterns.append({
                'name': 'Overtrading',
                'description': 'Taking too many trades, potentially reducing quality.',
                'impact': 'negative',
                'frequency': min(100, avg_trades_per_day * 30),
                'impactScore': 6
            })
    
    # Time-based patterns
    morning_trades = [t for t in trades if t.date.hour < 12]
    afternoon_trades = [t for t in trades if t.date.hour >= 12]
    
    if morning_trades and afternoon_trades:
        morning_win_rate = len([t for t in morning_trades if t.pnl > 0]) / len(morning_trades) * 100
        afternoon_win_rate = len([t for t in afternoon_trades if t.pnl > 0]) / len(afternoon_trades) * 100
        
        if abs(morning_win_rate - afternoon_win_rate) > 20:
            better_time = "morning" if morning_win_rate > afternoon_win_rate else "afternoon"
            patterns.append({
                'name': f'Time Preference',
                'description': f'Better performance during {better_time} hours.',
                'impact': 'positive',
                'frequency': 80,
                'impactScore': 7
            })
    
    return patterns

def generate_recommendations(trades, win_rate, avg_win, avg_loss, max_drawdown):
    """Generate AI recommendations"""
    recommendations = []
    
    # Win rate recommendations
    if win_rate < 45:
        recommendations.append({
            'title': 'Improve Entry Quality',
            'description': 'Focus on higher probability setups with better confirmation signals.',
            'priority': 'High',
            'expectedImpact': '15-25% improvement in win rate',
            'details': 'Your current win rate suggests entry timing needs improvement. Consider waiting for stronger confirmation signals and avoiding low-probability setups.',
            'actions': [
                'Wait for multiple timeframe confirmation',
                'Use volume analysis for entry validation',
                'Avoid trading during low volatility periods',
                'Implement stricter entry criteria'
            ]
        })
    
    # Risk management recommendations
    if max_drawdown > 10:
        recommendations.append({
            'title': 'Strengthen Risk Management',
            'description': 'Implement stricter position sizing and stop loss rules.',
            'priority': 'High',
            'expectedImpact': 'Reduce drawdown by 30-50%',
            'details': 'Current drawdown levels indicate need for better risk control. Focus on position sizing and stop loss placement.',
            'actions': [
                'Reduce position size to 1-2% of account per trade',
                'Set stop losses at logical support/resistance levels',
                'Implement maximum daily loss limits',
                'Use trailing stops for winning trades'
            ]
        })
    
    # Risk-reward recommendations
    if avg_loss != 0 and abs(avg_win / avg_loss) < 2:
        recommendations.append({
            'title': 'Optimize Risk-Reward',
            'description': 'Improve exit strategy to achieve better risk-reward ratios.',
            'priority': 'Medium',
            'expectedImpact': 'Increase average win by 20-40%',
            'details': 'Your current risk-reward ratio is below optimal levels. Focus on letting winners run and cutting losses quickly.',
            'actions': [
                'Set take profit targets at 2:1 or better risk-reward',
                'Use partial profit taking at key levels',
                'Implement trailing stops for winners',
                'Review and adjust exit criteria'
            ]
        })
    
    # Consistency recommendations
    if len(trades) >= 10:
        recent_performance = trades[-10:]
        recent_win_rate = len([t for t in recent_performance if t.pnl > 0]) / len(recent_performance) * 100
        if abs(recent_win_rate - win_rate) > 15:
            recommendations.append({
                'title': 'Maintain Consistency',
                'description': 'Recent performance shows inconsistency. Review and standardize your approach.',
                'priority': 'Medium',
                'expectedImpact': 'Improve consistency and reduce variance',
                'details': 'Your recent performance differs significantly from your overall average, indicating inconsistency in your approach.',
                'actions': [
                    'Document your trading plan and stick to it',
                    'Review recent trades for deviations from your strategy',
                    'Implement a trading checklist for each trade',
                    'Track emotional state during trades'
                ]
            })
    
    return recommendations

def analyze_optimal_times(trades):
    """Analyze optimal trading times"""
    if not trades:
        return []
    
    # Group trades by hour
    hourly_performance = {}
    for trade in trades:
        hour = trade.date.hour
        if hour not in hourly_performance:
            hourly_performance[hour] = {'trades': [], 'pnl': 0}
        hourly_performance[hour]['trades'].append(trade)
        hourly_performance[hour]['pnl'] += trade.pnl
    
    # Calculate win rates and average P&L by hour
    optimal_times = []
    for hour, data in hourly_performance.items():
        if len(data['trades']) >= 3:  # Only include hours with sufficient data
            win_rate = len([t for t in data['trades'] if t.pnl > 0]) / len(data['trades']) * 100
            avg_pnl = data['pnl'] / len(data['trades'])
            
            period_name = f"{hour:02d}:00"
            if hour < 12:
                period_name = f"{hour:02d}:00 AM"
            else:
                period_name = f"{hour-12:02d}:00 PM" if hour > 12 else "12:00 PM"
            
            optimal_times.append({
                'period': period_name,
                'winRate': round(win_rate, 1),
                'avgPnl': round(avg_pnl, 2)
            })
    
    # Sort by win rate
    optimal_times.sort(key=lambda x: x['winRate'], reverse=True)
    
    return optimal_times[:8]  # Return top 8 time periods

def calculate_improvement_potential(trades, win_rate, avg_win, avg_loss):
    """Calculate improvement potential percentage"""
    if not trades:
        return 0
    
    # Base potential on current performance gaps
    potential = 0
    
    # Win rate potential (target: 55%)
    if win_rate < 55:
        potential += (55 - win_rate) * 2
    
    # Risk-reward potential (target: 2:1)
    if avg_loss != 0:
        current_rr = abs(avg_win / avg_loss)
        if current_rr < 2:
            potential += (2 - current_rr) * 15
    
    # Consistency potential
    if len(trades) >= 10:
        recent_trades = trades[-10:]
        recent_win_rate = len([t for t in recent_trades if t.pnl > 0]) / len(recent_trades) * 100
        if abs(recent_win_rate - win_rate) > 15:
            potential += 20
    
    return min(100, potential)

def predict_next_best_setup(trades):
    """Predict the next best trading setup"""
    if not trades:
        return "Insufficient data", 0
    
    # Analyze recent winning patterns
    recent_wins = [t for t in trades[-20:] if t.pnl > 0]  # Last 20 winning trades
    
    if not recent_wins:
        return "Focus on risk management", 30
    
    # Find most common winning characteristics
    winning_symbols = [t.symbol for t in recent_wins]
    winning_directions = [t.direction for t in recent_wins]
    
    if winning_symbols:
        most_common_symbol = max(set(winning_symbols), key=winning_symbols.count)
        symbol_confidence = winning_symbols.count(most_common_symbol) / len(winning_symbols) * 100
    else:
        most_common_symbol = "Any"
        symbol_confidence = 50
    
    if winning_directions:
        most_common_direction = max(set(winning_directions), key=winning_directions.count)
        direction_confidence = winning_directions.count(most_common_direction) / len(winning_directions) * 100
    else:
        most_common_direction = "Any"
        direction_confidence = 50
    
    setup_name = f"{most_common_symbol} {most_common_direction.upper()}"
    confidence = (symbol_confidence + direction_confidence) / 2
    
    return setup_name, confidence

@journal_bp.route('/debug/trades', methods=['GET'])
@jwt_required()
def debug_trades():
    """Debug endpoint to check trade data and profile issues"""
    try:
        user_id = int(get_jwt_identity())
        
        # Get all trades for user (without profile filter)
        # Use group-aware query
        current_user = User.query.get(user_id)
        if current_user and current_user.account_type == "group" and current_user.group_id:
            # Get individual members
            group_members = User.query.filter_by(group_id=current_user.group_id, account_type="individual").all()
            user_ids = [member.id for member in group_members]
            # Also include the group account itself (for imported trades)
            user_ids.append(user_id)
            
            if user_ids:
                query = JournalEntry.query.filter(JournalEntry.user_id.in_(user_ids))
                all_trades = query.all()
            else:
                all_trades = JournalEntry.query.filter_by(user_id=user_id).all()
        else:
            all_trades = JournalEntry.query.filter_by(user_id=user_id).all()
        
        # Get trades with profile_id
        if current_user and current_user.account_type == "group" and current_user.group_id:
            trades_with_profile = JournalEntry.query.filter(
                JournalEntry.user_id.in_(user_ids),
                JournalEntry.profile_id.isnot(None)
            ).all()
            
            # Get trades without profile_id
            trades_without_profile = JournalEntry.query.filter(
                JournalEntry.user_id.in_(user_ids),
                JournalEntry.profile_id.is_(None)
            ).all()
        else:
            trades_with_profile = JournalEntry.query.filter(
                JournalEntry.user_id == user_id,
                JournalEntry.profile_id.isnot(None)
            ).all()
            
            # Get trades without profile_id
            trades_without_profile = JournalEntry.query.filter(
                JournalEntry.user_id == user_id,
                JournalEntry.profile_id.is_(None)
            ).all()
        
        # Get active profile
        active_profile = Profile.query.filter_by(user_id=user_id, is_active=True).first()
        
        # Get all profiles for user
        all_profiles = Profile.query.filter_by(user_id=user_id).all()
        
        return jsonify({
            'total_trades': len(all_trades),
            'trades_with_profile': len(trades_with_profile),
            'trades_without_profile': len(trades_without_profile),
            'active_profile': {
                'id': active_profile.id if active_profile else None,
                'name': active_profile.name if active_profile else None,
                'is_active': active_profile.is_active if active_profile else None
            },
            'all_profiles': [{
                'id': p.id,
                'name': p.name,
                'is_active': p.is_active
            } for p in all_profiles],
            'sample_trades': [{
                'id': t.id,
                'symbol': t.symbol,
                'pnl': t.pnl,
                'date': t.date.isoformat() if t.date else None,
                'profile_id': t.profile_id,
                'user_id': t.user_id
            } for t in all_trades[:5]]  # Show first 5 trades
        })
        
    except Exception as e:
        print("Debug trades error:", e)
        return jsonify({'error': str(e)}), 500

@journal_bp.route('/fix-profile-data', methods=['POST'])
@jwt_required()
def fix_profile_data():
    """Fix trades that don't have profile_id assigned"""
    try:
        user_id = int(get_jwt_identity())
        
        # Get or create active profile
        active_profile = Profile.query.filter_by(user_id=user_id, is_active=True).first()
        if not active_profile:
            # Create default profile if none exists
            active_profile = Profile(
                user_id=user_id,
                name="Default Profile",
                description="Default trading profile",
                is_active=True
            )
            db.session.add(active_profile)
            db.session.flush()  # Get the ID
        
        # Update all trades without profile_id
        # Use group-aware query
        current_user = User.query.get(user_id)
        if current_user and current_user.account_type == "group" and current_user.group_id:
            # Get individual members
            group_members = User.query.filter_by(group_id=current_user.group_id, account_type="individual").all()
            user_ids = [member.id for member in group_members]
            # Also include the group account itself (for imported trades)
            user_ids.append(user_id)
            
            if user_ids:
                updated_count = JournalEntry.query.filter(
                    JournalEntry.user_id.in_(user_ids),
                    JournalEntry.profile_id.is_(None)
                ).update({'profile_id': active_profile.id})
                
                # Update all import batches without profile_id
                batch_updated_count = ImportBatch.query.filter(
                    ImportBatch.user_id.in_(user_ids),
                    ImportBatch.profile_id.is_(None)
                ).update({'profile_id': active_profile.id})
            else:
                updated_count = JournalEntry.query.filter(
                    JournalEntry.user_id == user_id,
                    JournalEntry.profile_id.is_(None)
                ).update({'profile_id': active_profile.id})
                
                # Update all import batches without profile_id
                batch_updated_count = ImportBatch.query.filter(
                    ImportBatch.user_id == user_id,
                    ImportBatch.profile_id.is_(None)
                ).update({'profile_id': active_profile.id})
        else:
            updated_count = JournalEntry.query.filter(
                JournalEntry.user_id == user_id,
                JournalEntry.profile_id.is_(None)
            ).update({'profile_id': active_profile.id})
            
            # Update all import batches without profile_id
            batch_updated_count = ImportBatch.query.filter(
                ImportBatch.user_id == user_id,
                ImportBatch.profile_id.is_(None)
            ).update({'profile_id': active_profile.id})
        
        db.session.commit()
        
        return jsonify({
            'message': f'Fixed {updated_count} trades and {batch_updated_count} import batches',
            'assigned_profile_id': active_profile.id,
            'assigned_profile_name': active_profile.name
        })
        
    except Exception as e:
        db.session.rollback()
        print("Fix profile data error:", e)
        return jsonify({'error': str(e)}), 500


# ─── Custom Variables Management ───────────────────────────────────────────────

@journal_bp.route('/custom-variables', methods=['GET'])
@jwt_required()
def get_custom_variables():
    """
    Get all custom variables for the current user and profile.
    For group members, also include group manager's variables.
    """
    try:
        print("🔍 Debug - get_custom_variables endpoint called")
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        
        print(f"🔍 Debug - User ID: {user_id}, Profile ID: {profile_id}")
        
        # Get current user to check account type
        current_user = User.query.get(user_id)
        if not current_user:
            print(f"🔍 Debug - User {user_id} not found")
            return jsonify({'error': 'User not found'}), 404
        
        # Get user's own variables
        profile = Profile.query.filter_by(user_id=user_id, id=profile_id).first()
        user_variables = {}
        if profile and profile.description and profile.description.startswith('VARS:'):
            try:
                user_variables = json.loads(profile.description[5:])
            except:
                user_variables = {}
        
        # If user is a group member, also get group manager's variables
        group_variables = {}
        if current_user.account_type == 'individual' and current_user.group_id:
            # Find group manager
            group_manager = User.query.filter_by(
                group_id=current_user.group_id,
                account_type='group'
            ).first()
            
            if group_manager:
                # Get group manager's active profile, or any profile if none is active
                group_manager_profile = Profile.query.filter_by(
                    user_id=group_manager.id,
                    is_active=True
                ).first()
                
                # If no active profile, get the first available profile
                if not group_manager_profile:
                    group_manager_profile = Profile.query.filter_by(
                        user_id=group_manager.id
                    ).first()
                
                if group_manager_profile and group_manager_profile.description and group_manager_profile.description.startswith('VARS:'):
                    try:
                        group_variables = json.loads(group_manager_profile.description[5:])
                    except:
                        group_variables = {}
        
        # Combine user variables and group variables
        # Group variables take precedence (can override user variables)
        all_variables = {**user_variables, **group_variables}
        
        print(f"🔍 Debug - User variables: {user_variables}")
        print(f"🔍 Debug - Group variables: {group_variables}")
        print(f"🔍 Debug - Final variables: {all_variables}")
        
        return jsonify(all_variables), 200
        
    except Exception as e:
        print(f"Error getting custom variables: {e}")
        return jsonify({'error': str(e)}), 500

@journal_bp.route('/custom-variables', methods=['POST'])
@jwt_required()
def create_custom_variable():
    """
    Create a new custom variable with values.
    For group managers, this creates group-wide variables.
    For individual users, this creates personal variables.
    """
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        data = request.get_json()
        
        var_name = data.get('name', '').strip().lower()
        values = data.get('values', [])
        
        if not var_name:
            return jsonify({'error': 'Variable name is required'}), 400
        
        if not values or not isinstance(values, list):
            return jsonify({'error': 'At least one value is required'}), 400
        
        # Clean and validate values
        cleaned_values = []
        for value in values:
            if value and str(value).strip():
                cleaned_values.append(str(value).strip())
        
        if not cleaned_values:
            return jsonify({'error': 'At least one valid value is required'}), 400
        
        # Get current user to check account type
        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Store variable definition in user's profile
        profile = Profile.query.filter_by(user_id=user_id, id=profile_id).first()
        if not profile:
            return jsonify({'error': 'Profile not found'}), 404
        
        # Get existing variable definitions
        existing_vars = {}
        if profile.description and profile.description.startswith('VARS:'):
            try:
                existing_vars = json.loads(profile.description[5:])
            except:
                existing_vars = {}
        
        # Add new variable
        existing_vars[var_name] = cleaned_values
        
        # Update profile description
        profile.description = 'VARS:' + json.dumps(existing_vars)
        db.session.commit()
        
        # Create response message based on account type
        if current_user.account_type == 'group':
            message = f'Group variable "{var_name}" created with {len(cleaned_values)} values. All group members will see this variable.'
        else:
            message = f'Custom variable "{var_name}" created with {len(cleaned_values)} values'
        
        return jsonify({
            'message': message,
            'variable': {
                'name': var_name,
                'values': cleaned_values
            },
            'is_group_variable': current_user.account_type == 'group'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating custom variable: {e}")
        return jsonify({'error': str(e)}), 500

@journal_bp.route('/custom-variables/<var_name>', methods=['PUT'])
@jwt_required()
def update_custom_variable(var_name):
    """
    Update an existing custom variable with new values.
    For group managers, this updates group-wide variables.
    """
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        data = request.get_json()
        
        values = data.get('values', [])
        
        if not values or not isinstance(values, list):
            return jsonify({'error': 'At least one value is required'}), 400
        
        # Clean and validate values
        cleaned_values = []
        for value in values:
            if value and str(value).strip():
                cleaned_values.append(str(value).strip())
        
        if not cleaned_values:
            return jsonify({'error': 'At least one valid value is required'}), 400
        
        # Get current user to check account type
        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get profile and update variable
        profile = Profile.query.filter_by(user_id=user_id, id=profile_id).first()
        if not profile:
            return jsonify({'error': 'Profile not found'}), 404
        
        # Get existing variable definitions
        existing_vars = {}
        if profile.description and profile.description.startswith('VARS:'):
            try:
                existing_vars = json.loads(profile.description[5:])
            except:
                existing_vars = {}
        
        # Check if variable exists
        if var_name not in existing_vars:
            return jsonify({'error': f'Variable "{var_name}" not found'}), 404
        
        # Update the variable
        existing_vars[var_name] = cleaned_values
        
        # Update profile description
        profile.description = 'VARS:' + json.dumps(existing_vars)
        db.session.commit()
        
        # Create response message based on account type
        if current_user.account_type == 'group':
            message = f'Group variable "{var_name}" updated with {len(cleaned_values)} values. All group members will see the updated variable.'
        else:
            message = f'Custom variable "{var_name}" updated with {len(cleaned_values)} values'
        
        return jsonify({
            'message': message,
            'variable': {
                'name': var_name,
                'values': cleaned_values
            },
            'is_group_variable': current_user.account_type == 'group'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating custom variable: {e}")
        return jsonify({'error': str(e)}), 500

@journal_bp.route('/initial-balance', methods=['POST'])
@jwt_required()
def save_initial_balance():
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        data = request.get_json()
        
        if not data or 'initial_balance' not in data:
            return jsonify({"error": "Initial balance is required"}), 400
        
        initial_balance = data['initial_balance']
        
        # Validate the initial balance
        try:
            initial_balance = float(initial_balance)
            if initial_balance < 0:
                return jsonify({"error": "Initial balance must be positive"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid initial balance value"}), 400
        
        # Update the profile's initial balance
        profile = Profile.query.filter_by(user_id=user_id, id=profile_id).first()
        if not profile:
            return jsonify({"error": "Profile not found"}), 404
        
        profile.initial_balance = initial_balance
        db.session.commit()
        
        return jsonify({
            "message": "Initial balance saved successfully",
            "initial_balance": initial_balance
        }), 200
        
    except Exception as e:
        print(f"Error saving initial balance: {e}")
        return jsonify({"error": "Failed to save initial balance"}), 500


@journal_bp.route('/initial-balance', methods=['GET'])
@jwt_required()
def get_initial_balance():
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        
        profile = Profile.query.filter_by(user_id=user_id, id=profile_id).first()
        if not profile:
            return jsonify({"error": "Profile not found"}), 404
        
        return jsonify({
            "initial_balance": float(profile.initial_balance or 0.0)
        }), 200
        
    except Exception as e:
        print(f"Error getting initial balance: {e}")
        return jsonify({"error": "Failed to get initial balance"}), 500


@journal_bp.route('/custom-variables/<var_name>', methods=['DELETE'])
@jwt_required()
def delete_custom_variable(var_name):
    """
    Delete a custom variable (this will remove it from all trades).
    For group managers, this deletes group-wide variables.
    """
    try:
        user_id = int(get_jwt_identity())
        profile_id = get_active_profile_id(user_id)
        
        # Get current user to check account type
        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get profile and remove variable
        profile = Profile.query.filter_by(user_id=user_id, id=profile_id).first()
        if not profile:
            return jsonify({'error': 'Profile not found'}), 404
        
        # Get existing variable definitions
        existing_vars = {}
        if profile.description and profile.description.startswith('VARS:'):
            try:
                existing_vars = json.loads(profile.description[5:])
            except:
                existing_vars = {}
        
        # Check if variable exists
        if var_name not in existing_vars:
            return jsonify({'error': f'Variable "{var_name}" not found'}), 404
        
        # Remove the variable from all trades
        if current_user.account_type == 'group':
            # For group managers, remove from all group members' trades
            group_members = User.query.filter_by(
                group_id=current_user.group_id,
                account_type='individual'
            ).all()
            user_ids = [member.id for member in group_members]
            
            if user_ids:
                entries = JournalEntry.query.filter(
                    JournalEntry.user_id.in_(user_ids)
                ).all()
            else:
                entries = []
        else:
            # For individual users, remove from their own trades
            entries = JournalEntry.query.filter_by(user_id=user_id, profile_id=profile_id).all()
        
        updated_count = 0
        for entry in entries:
            if entry.variables and isinstance(entry.variables, dict) and var_name in entry.variables:
                del entry.variables[var_name]
                updated_count += 1
        
        # Remove the variable definition
        del existing_vars[var_name]
        
        # Update profile description
        profile.description = 'VARS:' + json.dumps(existing_vars)
        db.session.commit()
        
        # Create response message based on account type
        if current_user.account_type == 'group':
            message = f'Group variable "{var_name}" deleted from {updated_count} trades across all group members.'
        else:
            message = f'Custom variable "{var_name}" deleted from {updated_count} trades'
        
        return jsonify({
            'message': message,
            'is_group_variable': current_user.account_type == 'group'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting custom variable: {e}")
        return jsonify({'error': str(e)}), 500






@journal_bp.route('/screenshot/<filename>', methods=['GET'])
@jwt_required()
def serve_screenshot(filename):
    """Serve uploaded screenshot files"""
    try:
        return send_from_directory(SCREENSHOTS_FOLDER, filename)
    except Exception as e:
        print(f"Error serving screenshot {filename}: {e}")
        return jsonify({'error': 'File not found'}), 404


@journal_bp.route('/trade-duration-analysis', methods=['GET'])
@jwt_required()
def trade_duration_analysis():
    """Analyze trades by duration categories using open_time and close_time fields"""
    try:
        current_user_id = get_jwt_identity()
        profile_id = get_active_profile_id(current_user_id)
        
        # Get query parameters
        timeframe = request.args.get('timeframe', 'all')
        direction_filter = request.args.get('direction', 'all')  # all, long, short
        
        # Build base query
        query = build_group_aware_query(current_user_id, profile_id)
        
        # Apply filters
        if timeframe != 'all':
            if timeframe == 'daily':
                query = query.filter(JournalEntry.date >= datetime.utcnow().date())
            elif timeframe == 'weekly':
                week_ago = datetime.utcnow() - timedelta(days=7)
                query = query.filter(JournalEntry.date >= week_ago)
            elif timeframe == 'monthly':
                month_ago = datetime.utcnow() - timedelta(days=30)
                query = query.filter(JournalEntry.date >= month_ago)
        
        if direction_filter != 'all':
            query = query.filter(JournalEntry.direction == direction_filter)
        
        # Apply additional filters from request
        if request.args.get('from_date'):
            query = query.filter(JournalEntry.date >= datetime.fromisoformat(request.args.get('from_date')))
        if request.args.get('to_date'):
            query = query.filter(JournalEntry.date <= datetime.fromisoformat(request.args.get('to_date')))
        if request.args.get('symbols'):
            symbols = request.args.get('symbols').split(',')
            query = query.filter(JournalEntry.symbol.in_(symbols))
        if request.args.get('directions'):
            directions = request.args.get('directions').split(',')
            query = query.filter(JournalEntry.direction.in_(directions))
        if request.args.get('strategies'):
            strategies = request.args.get('strategies').split(',')
            query = query.filter(JournalEntry.strategy.in_(strategies))
        if request.args.get('setups'):
            setups = request.args.get('setups').split(',')
            query = query.filter(JournalEntry.setup.in_(setups))
        if request.args.get('min_pnl'):
            try:
                min_pnl = float(request.args.get('min_pnl'))
                if not math.isnan(min_pnl):
                    query = query.filter(JournalEntry.pnl >= min_pnl)
            except (ValueError, TypeError):
                pass
        if request.args.get('max_pnl'):
            try:
                max_pnl = float(request.args.get('max_pnl'))
                if not math.isnan(max_pnl):
                    query = query.filter(JournalEntry.pnl <= max_pnl)
            except (ValueError, TypeError):
                pass
        if request.args.get('min_rr'):
            try:
                min_rr = float(request.args.get('min_rr'))
                if not math.isnan(min_rr):
                    query = query.filter(JournalEntry.rr >= min_rr)
            except (ValueError, TypeError):
                pass
        if request.args.get('max_rr'):
            try:
                max_rr = float(request.args.get('max_rr'))
                if not math.isnan(max_rr):
                    query = query.filter(JournalEntry.rr <= max_rr)
            except (ValueError, TypeError):
                pass
        if request.args.get('batch_ids'):
            batch_ids = [int(x) for x in request.args.get('batch_ids').split(',')]
            query = query.filter(JournalEntry.import_batch_id.in_(batch_ids))
        
        trades = query.all()
        
        # Define duration categories with more granular breakdowns
        duration_categories = [
            {'name': 'Under 15 sec', 'min': 0, 'max': 15},
            {'name': '15-45 sec', 'min': 15, 'max': 45},
            {'name': '45 sec - 1 min', 'min': 45, 'max': 60},
            {'name': '1 min - 2 min', 'min': 60, 'max': 120},
            {'name': '2 min - 5 min', 'min': 120, 'max': 300},
            {'name': '5 min - 10 min', 'min': 300, 'max': 600},
            {'name': '10 min - 30 min', 'min': 600, 'max': 1800},
            {'name': '30 min - 1 hour', 'min': 1800, 'max': 3600},
            {'name': '1 hour - 2 hours', 'min': 3600, 'max': 7200},
            {'name': '2 hours - 4 hours', 'min': 7200, 'max': 14400},
            {'name': '4 hours and up', 'min': 14400, 'max': float('inf')}
        ]
        
        # Initialize results with enhanced metrics
        duration_analysis = {}
        for category in duration_categories:
            duration_analysis[category['name']] = {
                'trades': [],
                'total_pnl': 0,
                'trade_count': 0,
                'win_count': 0,
                'win_rate': 0,
                'avg_pnl': 0,
                'avg_rr': 0,
                'total_rr': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'max_win': 0,
                'max_loss': 0,
                'total_wins': 0,
                'total_losses': 0,
                'profit_factor': 0,
                'expectancy': 0
            }
        
        # Track trades with and without duration data
        trades_with_duration = 0
        trades_without_duration = 0
        total_trades_processed = 0
        
        # Categorize trades by duration
        for trade in trades:
            total_trades_processed += 1
            
            # Check if trade has duration data
            if (trade.open_time is None or trade.close_time is None or 
                trade.pnl is None or math.isnan(trade.pnl)):
                trades_without_duration += 1
                continue
                
            try:
                duration_seconds = (trade.close_time - trade.open_time).total_seconds()
                
                # Skip if duration is negative or invalid
                if duration_seconds < 0 or math.isnan(duration_seconds):
                    trades_without_duration += 1
                    continue
                
                trades_with_duration += 1
                
                # Find the appropriate category
                for category in duration_categories:
                    if category['min'] <= duration_seconds < category['max']:
                        category_name = category['name']
                        duration_analysis[category_name]['trades'].append(trade)
                        duration_analysis[category_name]['total_pnl'] += float(trade.pnl)
                        duration_analysis[category_name]['trade_count'] += 1
                        duration_analysis[category_name]['total_rr'] += float(trade.rr or 0)
                        
                        if float(trade.pnl) > 0:
                            duration_analysis[category_name]['win_count'] += 1
                            duration_analysis[category_name]['total_wins'] += float(trade.pnl)
                            duration_analysis[category_name]['avg_win'] = duration_analysis[category_name]['total_wins'] / duration_analysis[category_name]['win_count']
                            if float(trade.pnl) > duration_analysis[category_name]['max_win']:
                                duration_analysis[category_name]['max_win'] = float(trade.pnl)
                        else:
                            duration_analysis[category_name]['total_losses'] += abs(float(trade.pnl))
                            if abs(float(trade.pnl)) > duration_analysis[category_name]['max_loss']:
                                duration_analysis[category_name]['max_loss'] = abs(float(trade.pnl))
                        break
            except (TypeError, ValueError, AttributeError) as e:
                print(f"Error processing trade {trade.id}: {e}")
                trades_without_duration += 1
                continue
        
        # Calculate enhanced metrics for each category
        for category_name, data in duration_analysis.items():
            if data['trade_count'] > 0:
                data['avg_pnl'] = data['total_pnl'] / data['trade_count']
                data['win_rate'] = (data['win_count'] / data['trade_count']) * 100
                data['avg_rr'] = data['total_rr'] / data['trade_count']
                
                # Calculate profit factor
                if data['total_losses'] > 0:
                    data['profit_factor'] = data['total_wins'] / data['total_losses']
                else:
                    data['profit_factor'] = float('inf') if data['total_wins'] > 0 else 0
                
                # Calculate expectancy
                data['expectancy'] = (data['avg_win'] * (data['win_rate'] / 100)) - (data['avg_loss'] * ((100 - data['win_rate']) / 100))
                
                # Calculate average loss
                loss_count = data['trade_count'] - data['win_count']
                if loss_count > 0:
                    data['avg_loss'] = data['total_losses'] / loss_count
                else:
                    data['avg_loss'] = 0
            else:
                data['avg_pnl'] = 0
                data['win_rate'] = 0
                data['avg_rr'] = 0
                data['profit_factor'] = 0
                data['expectancy'] = 0
                data['avg_loss'] = 0
        
        # Calculate overall metrics
        total_trades = sum(data['trade_count'] for data in duration_analysis.values())
        total_pnl = sum(data['total_pnl'] for data in duration_analysis.values())
        total_wins = sum(data['win_count'] for data in duration_analysis.values())
        
        # Ensure we don't have NaN values
        if math.isnan(total_pnl):
            total_pnl = 0.0
        if math.isnan(total_trades):
            total_trades = 0
        if math.isnan(total_wins):
            total_wins = 0
            
        overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        
        # Find best and worst performing duration categories
        best_category = None
        worst_category = None
        best_profit_factor = 0
        worst_profit_factor = float('inf')
        
        for category_name, data in duration_analysis.items():
            if data['trade_count'] > 0:
                if data['profit_factor'] > best_profit_factor:
                    best_profit_factor = data['profit_factor']
                    best_category = category_name
                if data['profit_factor'] < worst_profit_factor and data['profit_factor'] > 0:
                    worst_profit_factor = data['profit_factor']
                    worst_category = category_name
        
        # Prepare chart data
        performance_data = []
        count_data = []
        win_rate_data = []
        profit_factor_data = []
        
        for category_name, data in duration_analysis.items():
            if data['trade_count'] > 0:
                performance_data.append({
                    'duration': category_name,
                    'pnl': data['total_pnl']
                })
                
                count_data.append({
                    'duration': category_name,
                    'count': data['trade_count']
                })
                
                win_rate_data.append({
                    'duration': category_name,
                    'win_rate': data['win_rate']
                })
                
                profit_factor_data.append({
                    'duration': category_name,
                    'profit_factor': data['profit_factor'] if data['profit_factor'] != float('inf') else 10.0
                })
        
        # Data quality insights
        data_quality = {
            'total_trades_processed': total_trades_processed,
            'trades_with_duration': trades_with_duration,
            'trades_without_duration': trades_without_duration,
            'duration_coverage_percentage': (trades_with_duration / total_trades_processed * 100) if total_trades_processed > 0 else 0
        }
        
        # Helper function to sanitize JSON data (replace Infinity with None)
        def sanitize_json(obj):
            if isinstance(obj, dict):
                return {k: sanitize_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [sanitize_json(item) for item in obj]
            elif isinstance(obj, float) and (math.isinf(obj) or math.isnan(obj)):
                return None
            else:
                return obj
        
        response_data = {
            'success': True,
            'data': {
                'performance_by_duration': performance_data,
                'count_by_duration': count_data,
                'win_rate_by_duration': win_rate_data,
                'profit_factor_by_duration': profit_factor_data,
                'overall_win_rate': overall_win_rate,
                'total_trades': total_trades,
                'total_pnl': total_pnl,
                'duration_categories': duration_categories,
                'data_quality': data_quality,
                'insights': {
                    'best_duration_category': best_category,
                    'worst_duration_category': worst_category,
                    'best_profit_factor': best_profit_factor if best_profit_factor != float('inf') else None,
                    'worst_profit_factor': worst_profit_factor if worst_profit_factor != float('inf') else None
                }
            }
        }
        
        # Sanitize the response data to remove any Infinity or NaN values
        sanitized_data = sanitize_json(response_data)
        
        return jsonify(sanitized_data)
        
    except Exception as e:
        # print(f"Trade duration analysis error: {e}")
        # import traceback
        # traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@journal_bp.route('/trade-duration-insights', methods=['GET'])
@jwt_required()
def trade_duration_insights():
    """Provide detailed insights and recommendations based on trade duration analysis"""
    try:
        current_user_id = get_jwt_identity()
        profile_id = get_active_profile_id(current_user_id)
        
        # Get query parameters
        timeframe = request.args.get('timeframe', 'all')
        direction_filter = request.args.get('direction', 'all')
        
        # Build base query
        query = JournalEntry.query.filter_by(user_id=current_user_id, profile_id=profile_id)
        
        # Apply filters (same as trade-duration-analysis)
        if timeframe != 'all':
            if timeframe == 'daily':
                query = query.filter(JournalEntry.date >= datetime.utcnow().date())
            elif timeframe == 'weekly':
                week_ago = datetime.utcnow() - timedelta(days=7)
                query = query.filter(JournalEntry.date >= week_ago)
            elif timeframe == 'monthly':
                month_ago = datetime.utcnow() - timedelta(days=30)
                query = query.filter(JournalEntry.date >= month_ago)
        
        if direction_filter != 'all':
            query = query.filter(JournalEntry.direction == direction_filter)
        
        # Apply additional filters
        if request.args.get('from_date'):
            query = query.filter(JournalEntry.date >= datetime.fromisoformat(request.args.get('from_date')))
        if request.args.get('to_date'):
            query = query.filter(JournalEntry.date <= datetime.fromisoformat(request.args.get('to_date')))
        if request.args.get('symbols'):
            symbols = request.args.get('symbols').split(',')
            query = query.filter(JournalEntry.symbol.in_(symbols))
        if request.args.get('strategies'):
            strategies = request.args.get('strategies').split(',')
            query = query.filter(JournalEntry.strategy.in_(strategies))
        
        trades = query.all()
        
        # Collect duration data
        duration_data = []
        trades_with_duration = 0
        total_trades = len(trades)
        
        for trade in trades:
            if (trade.open_time is None or trade.close_time is None or 
                trade.pnl is None or math.isnan(trade.pnl)):
                continue
                
            try:
                duration_seconds = (trade.close_time - trade.open_time).total_seconds()
                if duration_seconds < 0 or math.isnan(duration_seconds):
                    continue
                    
                trades_with_duration += 1
                duration_data.append({
                    'duration_seconds': duration_seconds,
                    'duration_minutes': duration_seconds / 60,
                    'pnl': float(trade.pnl),
                    'rr': float(trade.rr or 0),
                    'symbol': trade.symbol,
                    'direction': trade.direction,
                    'strategy': trade.strategy,
                    'setup': trade.setup,
                    'is_win': float(trade.pnl) > 0
                })
            except (TypeError, ValueError, AttributeError):
                continue
        
        if not duration_data:
            return jsonify({
                'success': True,
                'insights': {
                    'message': 'No trades with valid duration data found. Please add Open Time and Close Time to your trades for detailed duration insights.',
                    'data_quality': {
                        'total_trades': total_trades,
                        'trades_with_duration': 0,
                        'coverage_percentage': 0
                    }
                }
            })
        
        # Calculate duration statistics
        durations = [d['duration_minutes'] for d in duration_data]
        avg_duration = sum(durations) / len(durations)
        median_duration = sorted(durations)[len(durations) // 2]
        
        # Find optimal duration ranges
        winning_trades = [d for d in duration_data if d['is_win']]
        losing_trades = [d for d in duration_data if not d['is_win']]
        
        win_durations = [d['duration_minutes'] for d in winning_trades]
        loss_durations = [d['duration_minutes'] for d in losing_trades]
        
        avg_win_duration = sum(win_durations) / len(win_durations) if win_durations else 0
        avg_loss_duration = sum(loss_durations) / len(loss_durations) if loss_durations else 0
        
        # Duration distribution analysis
        duration_ranges = {
            'scalping': {'min': 0, 'max': 5, 'name': 'Scalping (0-5 min)'},
            'day_trading': {'min': 5, 'max': 240, 'name': 'Day Trading (5-240 min)'},
            'swing_trading': {'min': 240, 'max': 1440, 'name': 'Swing Trading (4-24 hours)'},
            'position_trading': {'min': 1440, 'max': float('inf'), 'name': 'Position Trading (24h+)'}
        }
        
        range_performance = {}
        for range_key, range_info in duration_ranges.items():
            range_trades = [d for d in duration_data 
                          if range_info['min'] <= d['duration_minutes'] < range_info['max']]
            
            if range_trades:
                wins = [t for t in range_trades if t['is_win']]
                total_pnl = sum(t['pnl'] for t in range_trades)
                avg_rr = sum(t['rr'] for t in range_trades) / len(range_trades)
                
                range_performance[range_key] = {
                    'name': range_info['name'],
                    'trade_count': len(range_trades),
                    'win_count': len(wins),
                    'win_rate': (len(wins) / len(range_trades)) * 100,
                    'total_pnl': total_pnl,
                    'avg_pnl': total_pnl / len(range_trades),
                    'avg_rr': avg_rr,
                    'avg_duration': sum(t['duration_minutes'] for t in range_trades) / len(range_trades)
                }
        
        # Find best performing duration range
        best_range = None
        best_profit_factor = 0
        
        for range_key, data in range_performance.items():
            if data['trade_count'] >= 3:  # Minimum sample size
                loss_count = data['trade_count'] - data['win_count']
                if loss_count > 0:
                    profit_factor = (data['win_count'] * data['avg_pnl']) / (loss_count * abs(data['avg_pnl']))
                    if profit_factor > best_profit_factor:
                        best_profit_factor = profit_factor
                        best_range = range_key
        
        # Generate insights and recommendations
        insights = {
            'data_quality': {
                'total_trades': total_trades,
                'trades_with_duration': trades_with_duration,
                'coverage_percentage': (trades_with_duration / total_trades * 100) if total_trades > 0 else 0
            },
            'duration_statistics': {
                'average_duration_minutes': round(avg_duration, 2),
                'median_duration_minutes': round(median_duration, 2),
                'average_win_duration_minutes': round(avg_win_duration, 2),
                'average_loss_duration_minutes': round(avg_loss_duration, 2),
                'duration_difference': round(abs(avg_win_duration - avg_loss_duration), 2)
            },
            'range_performance': range_performance,
            'best_performing_range': best_range,
            'recommendations': []
        }
        
        # Generate recommendations
        if avg_win_duration > avg_loss_duration:
            insights['recommendations'].append({
                'type': 'duration_management',
                'title': 'Consider Holding Winners Longer',
                'description': f'Your winning trades average {round(avg_win_duration, 1)} minutes while losing trades average {round(avg_loss_duration, 1)} minutes. Consider letting your winning trades run longer.',
                'priority': 'high'
            })
        elif avg_loss_duration > avg_win_duration:
            insights['recommendations'].append({
                'type': 'duration_management',
                'title': 'Consider Exiting Losers Faster',
                'description': f'Your losing trades average {round(avg_loss_duration, 1)} minutes while winning trades average {round(avg_win_duration, 1)} minutes. Consider cutting losses more quickly.',
                'priority': 'high'
            })
        
        if best_range and range_performance[best_range]['win_rate'] > 60:
            insights['recommendations'].append({
                'type': 'strategy_optimization',
                'title': f'Focus on {range_performance[best_range]["name"]}',
                'description': f'Your {range_performance[best_range]["name"]} trades show a {round(range_performance[best_range]["win_rate"], 1)}% win rate. Consider focusing more on this time frame.',
                'priority': 'medium'
            })
        
        if insights['data_quality']['coverage_percentage'] < 50:
            insights['recommendations'].append({
                'type': 'data_quality',
                'title': 'Improve Duration Data Quality',
                'description': f'Only {round(insights["data_quality"]["coverage_percentage"], 1)}% of your trades have duration data. Add Open Time and Close Time to more trades for better insights.',
                'priority': 'high'
            })
        
        return jsonify({
            'success': True,
            'insights': insights
        })
        
    except Exception as e:
        print(f"Trade duration insights error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@journal_bp.route('/validate-duration-data', methods=['GET'])
@jwt_required()
def validate_duration_data():
    """Validate and provide insights about the quality of duration data"""
    try:
        current_user_id = get_jwt_identity()
        profile_id = get_active_profile_id(current_user_id)
        
        # Get all trades for the user
        trades = JournalEntry.query.filter_by(user_id=current_user_id, profile_id=profile_id).all()
        
        validation_results = {
            'total_trades': len(trades),
            'trades_with_open_time': 0,
            'trades_with_close_time': 0,
            'trades_with_both_times': 0,
            'trades_with_valid_duration': 0,
            'trades_with_invalid_duration': 0,
            'trades_with_negative_duration': 0,
            'trades_with_zero_duration': 0,
            'trades_with_extreme_duration': 0,
            'issues': []
        }
        
        for trade in trades:
            has_open = trade.open_time is not None
            has_close = trade.close_time is not None
            
            if has_open:
                validation_results['trades_with_open_time'] += 1
            if has_close:
                validation_results['trades_with_close_time'] += 1
            if has_open and has_close:
                validation_results['trades_with_both_times'] += 1
                
                try:
                    duration_seconds = (trade.close_time - trade.open_time).total_seconds()
                    
                    if duration_seconds < 0:
                        validation_results['trades_with_negative_duration'] += 1
                        validation_results['issues'].append({
                            'trade_id': trade.id,
                            'symbol': trade.symbol,
                            'issue': 'Negative duration (close time before open time)',
                            'open_time': trade.open_time.isoformat() if trade.open_time else None,
                            'close_time': trade.close_time.isoformat() if trade.close_time else None,
                            'duration_seconds': duration_seconds
                        })
                    elif duration_seconds == 0:
                        validation_results['trades_with_zero_duration'] += 1
                        validation_results['issues'].append({
                            'trade_id': trade.id,
                            'symbol': trade.symbol,
                            'issue': 'Zero duration (same open and close time)',
                            'open_time': trade.open_time.isoformat() if trade.open_time else None,
                            'close_time': trade.close_time.isoformat() if trade.close_time else None
                        })
                    elif duration_seconds > 86400 * 30:  # More than 30 days
                        validation_results['trades_with_extreme_duration'] += 1
                        validation_results['issues'].append({
                            'trade_id': trade.id,
                            'symbol': trade.symbol,
                            'issue': 'Extreme duration (more than 30 days)',
                            'open_time': trade.open_time.isoformat() if trade.open_time else None,
                            'close_time': trade.close_time.isoformat() if trade.close_time else None,
                            'duration_days': round(duration_seconds / 86400, 1)
                        })
                    else:
                        validation_results['trades_with_valid_duration'] += 1
                        
                except (TypeError, ValueError, AttributeError) as e:
                    validation_results['trades_with_invalid_duration'] += 1
                    validation_results['issues'].append({
                        'trade_id': trade.id,
                        'symbol': trade.symbol,
                        'issue': f'Invalid duration data: {str(e)}',
                        'open_time': trade.open_time.isoformat() if trade.open_time else None,
                        'close_time': trade.close_time.isoformat() if trade.close_time else None
                    })
        
        # Calculate percentages
        total = validation_results['total_trades']
        validation_results['coverage_percentage'] = (validation_results['trades_with_both_times'] / total * 100) if total > 0 else 0
        validation_results['valid_duration_percentage'] = (validation_results['trades_with_valid_duration'] / total * 100) if total > 0 else 0
        
        # Generate recommendations
        recommendations = []
        
        if validation_results['coverage_percentage'] < 50:
            recommendations.append({
                'priority': 'high',
                'title': 'Low Duration Data Coverage',
                'description': f'Only {round(validation_results["coverage_percentage"], 1)}% of your trades have both open and close times. Add these fields to improve duration analysis.',
                'action': 'Add Open Time and Close Time to more trades in your journal entries.'
            })
        
        if validation_results['trades_with_negative_duration'] > 0:
            recommendations.append({
                'priority': 'high',
                'title': 'Negative Duration Issues',
                'description': f'{validation_results["trades_with_negative_duration"]} trades have close times before open times.',
                'action': 'Review and correct the Open Time and Close Time for these trades.'
            })
        
        if validation_results['trades_with_zero_duration'] > 0:
            recommendations.append({
                'priority': 'medium',
                'title': 'Zero Duration Issues',
                'description': f'{validation_results["trades_with_zero_duration"]} trades have the same open and close time.',
                'action': 'Verify if these are correct or if the times need adjustment.'
            })
        
        if validation_results['trades_with_extreme_duration'] > 0:
            recommendations.append({
                'priority': 'medium',
                'title': 'Extreme Duration Values',
                'description': f'{validation_results["trades_with_extreme_duration"]} trades have durations longer than 30 days.',
                'action': 'Verify if these long durations are correct for your trading style.'
            })
        
        validation_results['recommendations'] = recommendations
        
        return jsonify({
            'success': True,
            'validation': validation_results
        })
        
    except Exception as e:
        print(f"Duration data validation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
