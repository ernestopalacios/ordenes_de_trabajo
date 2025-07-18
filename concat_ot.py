import logging
from quixstreams import Application
from quixstreams.models.serializers import JSONSerializer
from confluent_kafka import Message

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def on_consumer_error_handler(
    exc: Exception,
    msg: Message,
    logger: logging.Logger,
) -> bool:
    """
    Callback to handle exceptions during message deserialization.
    This will log the problematic message and allow the consumer to continue.
    """
    logger.error(
        f"Failed to deserialize message. Exception: {exc}\n"
        f"Topic: {msg.topic()}, Partition: {msg.partition()}, Offset: {msg.offset()}\n"
        f"Message value (raw): {msg.value()!r}"
    )
    # Returning True tells the consumer to ignore the message and continue.
    return True


# Quix Stream app configuration from your request
app = Application(
    broker_address="localhost:29092",
    consumer_group="concat",
    auto_create_topics=True,
    auto_offset_reset="earliest",
    loglevel="INFO",
    on_consumer_error=on_consumer_error_handler,
)

# Input topic from your request. Using value_deserializer for an input topic.
input_topic = app.topic("new_ot", value_serializer=JSONSerializer())

# Create a StreamingDataFrame
sdf = app.dataframe(input_topic)


def reducer(aggregated_values, new_value):
    """
    Append each new value to a list for batching.
    """
    aggregated_values.append(new_value)
    return aggregated_values


def process_batch(window_values):
    """
    Process the list of values from the closed window.
    """
    if not window_values:
        return

    logger.info(f"Procesando batch de {len(window_values)} mensajes.")
    # For demonstration, we'll just print the batch.
    # In a real application, you would perform your batch processing here.
    for i, value in enumerate(window_values):
        logger.info(f"  - Item {i+1}: {value}")


# Apply a 5-second tumbling window to batch messages
sdf = sdf.tumbling_window(duration_ms=5000)

# Use .reduce() to accumulate all messages within the window into a list
sdf = sdf.reduce(reducer=reducer, initializer=lambda value: [])

# Use .final() to process the accumulated list when the window closes
sdf = sdf.final().apply(process_batch)


def run_app():
    """Starts the Quix Streams application."""
    print("\n\n = = = =   Iniciando BATCH CONSUMER [Quix Streams application] ...  = = = =")
    app.run()
    print("\n\n = = = =   Se ha detenido [Quix Streams application] = = = =")


if __name__ == "__main__":
    try:
        run_app()
    except KeyboardInterrupt:
        print("\nSe ha detenido el consumidor manualmente.\n\n.")