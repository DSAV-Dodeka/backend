"""Modules encapsulate the different context functions in cases where the router function would become too complex.
They should not know about HTTP (that is for the actual routers and possible router helper functions), hence they
should raise only AppError exceptions and take in only model objects, a context and data source. They should NOT open
connections directly, that is for the lower data context functions to do."""
