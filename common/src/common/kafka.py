from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from .settings import settings

producer = None
consumer = None


async def get_kafka_producer() -> AIOKafkaProducer:
    global producer
    if producer is None:
        producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers
        )
        await producer.start()
    return producer


async def get_kafka_consumer(topics: list[str]) -> AIOKafkaConsumer:
    global consumer
    if consumer is None:
        consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_group_id
        )
        await consumer.start()
    return consumer


async def close_kafka():
    global producer, consumer
    if producer:
        await producer.stop()
    if consumer:
        await consumer.stop()