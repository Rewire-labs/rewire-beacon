"""Background workers — cleanup jobs and utility scripts.

RW-MESSAGING-23: dead Kafka workers (email_sender, sms_sender, push_sender,
whatsapp_sender) removed. The canonical async send path uses pgmq workers
in messaging_cp.queues (SenderWorker / RetryWorker) which use aio-pika /
RabbitMQ, not aiokafka. The Kafka workers were never wired to any Deployment
and aiokafka was not in deps.

Remaining workers: bad_token_cleanup.py, usage_reporter.py, whatsapp_template_sync.py.
"""
