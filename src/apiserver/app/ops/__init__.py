# This module is for functions with side effects that operate on data and also query data from the database
# However, they are still internal and should not directly return HTTP responses
# If they fail, they should consequently surface application-level errors, not error responses
