import quickfix as fix

def create_new_order_single(symbol, side, order_type, quantity, clordid):
    """
    Creates a FIX NewOrderSingle message.
    """
    message = fix.Message()
    header = message.getHeader()
    header.setField(fix.BeginString("FIX.4.4"))
    header.setField(fix.MsgType(fix.MsgType_NewOrderSingle))

    message.setField(fix.ClOrdID(clordid))
    message.setField(fix.Symbol(symbol))
    message.setField(fix.Side(side))
    message.setField(fix.OrderQty(quantity))
    message.setField(fix.OrdType(order_type))
    message.setField(fix.TransactTime())
    
    return message

def execution_report_to_dict(exec_report):
    """
    Converts a FIX ExecutionReport message to a Python dictionary.
    """
    report_dict = {}
    
    # Example fields to extract
    symbol = fix.Symbol()
    exec_report.getField(symbol)
    report_dict['symbol'] = symbol.getValue()
    
    side = fix.Side()
    exec_report.getField(side)
    report_dict['side'] = side.getValue()

    order_qty = fix.OrderQty()
    exec_report.getField(order_qty)
    report_dict['order_qty'] = order_qty.getValue()
    
    # Add more fields as needed
    
    return report_dict

def map_order_type_to_fix(internal_order_type):
    """
    Maps an internal order type to a FIX OrdType value.
    """
    mapping = {
        'MARKET': fix.OrdType_MARKET,
        'LIMIT': fix.OrdType_LIMIT,
        # Add other mappings
    }
    return mapping.get(internal_order_type.upper())

def translate_symbol_to_fix(internal_symbol):
    """
    Translates an internal instrument symbol to a FIX symbol.
    """
    # Placeholder for more complex symbol mapping logic
    return internal_symbol.upper()