"""
This module holds the shared state of the application, such as model caches,
to prevent circular import issues.
"""

# We store the model in a dictionary to be loaded during app startup
model_cache = {}
