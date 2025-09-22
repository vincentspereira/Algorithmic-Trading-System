def create_execution_intent(action, algorithm='VWAP', urgency='MEDIUM', time_in_force='GTC'):
    """
    Creates a high-level execution intent object.
    """
    return {
        'action': action,  # e.g., 'ENTER_LONG', 'EXIT_LONG'
        'algorithm': algorithm,
        'urgency': urgency,
        'time_in_force': time_in_force,
    }