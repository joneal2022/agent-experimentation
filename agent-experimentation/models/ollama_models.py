MODEL_CONFIG = {
    "data_analysis": "mistral:7b",
    "nlp": "nomic-embed-text",
    "alerting": "llama3:70b"
}
# This is a dictionary that maps different types of models to their respective configurations.
# The keys are the model types (e.g., "data_analysis", "nlp", "alerting") and the values are the model names (e.g., "mistral:7b", "nomic-embed-text", "llama3:70b").
# This configuration can be used to easily switch between different models based on the task at hand.