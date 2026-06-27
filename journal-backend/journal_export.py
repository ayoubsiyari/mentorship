"""Shared journal Excel export — same format as Journal page 'Export All Data'."""

import io
import json

import pandas as pd


def journal_entry_to_export_row(entry):
    """Build one export row matching /journal/export output exactly."""
    entry_datetime = entry.open_time.strftime('%Y-%m-%d %H:%M:%S') if entry.open_time else ''
    exit_datetime = entry.close_time.strftime('%Y-%m-%d %H:%M:%S') if entry.close_time else ''
    created_at = entry.created_at.strftime('%Y-%m-%d %H:%M:%S') if entry.created_at else ''
    updated_at = entry.updated_at.strftime('%Y-%m-%d %H:%M:%S') if entry.updated_at else ''
    trade_date = entry.date.strftime('%Y-%m-%d %H:%M:%S') if entry.date else ''

    variables_str = ''
    if entry.variables:
        try:
            variables_str = json.dumps(entry.variables)
        except Exception:
            variables_str = str(entry.variables)

    extra_data_str = ''
    if entry.extra_data:
        try:
            extra_data_str = json.dumps(entry.extra_data)
        except Exception:
            extra_data_str = str(entry.extra_data)

    var1 = entry.extra_data.get('var1', '') if entry.extra_data else ''
    var2 = entry.extra_data.get('var2', '') if entry.extra_data else ''
    var3 = entry.extra_data.get('var3', '') if entry.extra_data else ''
    var4 = entry.extra_data.get('var4', '') if entry.extra_data else ''
    var5 = entry.extra_data.get('var5', '') if entry.extra_data else ''
    var6 = entry.extra_data.get('var6', '') if entry.extra_data else ''
    var7 = entry.extra_data.get('var7', '') if entry.extra_data else ''
    var8 = entry.extra_data.get('var8', '') if entry.extra_data else ''
    var9 = entry.extra_data.get('var9', '') if entry.extra_data else ''
    var10 = entry.extra_data.get('var10', '') if entry.extra_data else ''

    setup = ''
    strategy_var = ''
    if entry.variables:
        setup = ', '.join(entry.variables.get('setup', [])) if entry.variables.get('setup') else ''
        strategy_var = ', '.join(entry.variables.get('strategy', [])) if entry.variables.get('strategy') else ''

    return {
        'symbol': entry.symbol,
        'direction': entry.direction,
        'entry_price': entry.entry_price,
        'exit_price': entry.exit_price,
        'stop_loss': entry.stop_loss,
        'take_profit': entry.take_profit,
        'high_price': entry.high_price,
        'low_price': entry.low_price,
        'quantity': entry.quantity,
        'contract_size': entry.contract_size,
        'instrument_type': entry.instrument_type,
        'risk_amount': entry.risk_amount,
        'pnl': entry.pnl,
        'rr': entry.rr,
        'strategy': entry.strategy or strategy_var,
        'setup': entry.setup or setup,
        'notes': entry.notes,
        'entry_datetime': entry_datetime,
        'exit_datetime': exit_datetime,
        'trade_date': trade_date,
        'created_at': created_at,
        'updated_at': updated_at,
        'duration_seconds': entry.duration_seconds,
        'duration_minutes': entry.duration_minutes,
        'duration_hours': entry.duration_hours,
        'duration_category': entry.duration_category,
        'commission': entry.commission,
        'slippage': entry.slippage,
        'entry_screenshot': entry.entry_screenshot,
        'exit_screenshot': entry.exit_screenshot,
        'var1': var1,
        'var2': var2,
        'var3': var3,
        'var4': var4,
        'var5': var5,
        'var6': var6,
        'var7': var7,
        'var8': var8,
        'var9': var9,
        'var10': var10,
        'variables_json': variables_str,
        'extra_data_json': extra_data_str,
        'id': entry.id,
        'import_batch_id': entry.import_batch_id,
    }


def create_journal_xlsx_bytes(entries):
    """Return xlsx bytes for a list of JournalEntry objects (same as user export)."""
    rows = [journal_entry_to_export_row(e) for e in entries]
    df = pd.DataFrame(rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Journal')
    output.seek(0)
    return output.getvalue()
