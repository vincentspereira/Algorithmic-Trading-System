from zero_trust_security import IdentityAccessManager
import inspect

# Get all methods of the class
methods = [method for method in dir(IdentityAccessManager) if not method.startswith('_')]
print('Methods in IdentityAccessManager:')
for method in methods:
    print(f'  {method}')