import quickfix as fix
import time

class FixClient(fix.Application):
    def onCreate(self, sessionID):
        print(f"Session created: {sessionID}")

    def onLogon(self, sessionID):
        self.sessionID = sessionID
        print(f"Logged on: {sessionID}")

    def onLogout(self, sessionID):
        print(f"Logged out: {sessionID}")

    def toAdmin(self, message, sessionID):
        print(f"To admin: {message}")

    def fromAdmin(self, message, sessionID):
        print(f"From admin: {message}")

    def toApp(self, message, sessionID):
        print(f"To app: {message}")

    def fromApp(self, message, sessionID):
        print(f"From app: {message}")
        # Basic message handling
        begin_string = fix.BeginString()
        message.getHeader().getField(begin_string)
        msg_type = fix.MsgType()
        message.getHeader().getField(msg_type)

        if msg_type.getValue() == fix.MsgType_ExecutionReport:
            self.handle_execution_report(message)

    def handle_execution_report(self, message):
        print("Received execution report:")
        # Extract and process execution report fields
        symbol = fix.Symbol()
        message.getField(symbol)
        print(f"- Symbol: {symbol.getValue()}")
        
    def send_order(self, symbol, side, order_type, quantity):
        # Create a new order single message
        message = fix.Message()
        header = message.getHeader()
        header.setField(fix.BeginString("FIX.4.4"))
        header.setField(fix.MsgType(fix.MsgType_NewOrderSingle))
        
        # Populate order fields
        message.setField(fix.ClOrdID("test-order-1"))
        message.setField(fix.Symbol(symbol))
        message.setField(fix.Side(side))
        message.setField(fix.OrderQty(quantity))
        message.setField(fix.OrdType(order_type))
        message.setField(fix.TransactTime())
        
        # Send the message
        fix.Session.sendToTarget(message, self.sessionID)
        print("Sent new order single")

def main():
    try:
        settings = fix.SessionSettings("config/fix/quickfixj-client.cfg")
        application = FixClient()
        store_factory = fix.FileStoreFactory(settings)
        log_factory = fix.FileLogFactory(settings)
        initiator = fix.SocketInitiator(application, store_factory, settings, log_factory)
        initiator.start()
        
        # Keep the application running
        while True:
            time.sleep(1)
            
    except fix.ConfigError as e:
        print(f"Configuration error: {e}")
    finally:
        if 'initiator' in locals() and initiator:
            initiator.stop()

if __name__ == "__main__":
    main()