from celery import Celery
from kombu import Exchange, Queue

app = Celery('tasks')
app.config_from_object('tasks.config')

dead_letter_queue_option = {  # TODO: finish code to use deadletter
    'x-dead-letter-exchange': 'dlx',
    'x-dead-letter-routing-key': 'dead_letter'
}

default_exchange = Exchange('default', type='direct')
dlx_exchange = Exchange('dlx', type='direct')

default_queue = Queue(
    'default',
    default_exchange,
    routing_key='default',
    queue_arguments=dead_letter_queue_option)
dead_letter_queue = Queue(
    'dead_letter', dlx_exchange, routing_key='dead_letter')

app.conf.task_queues = (default_queue, dead_letter_queue)

app.conf.task_default_queue = 'default'
app.conf.task_default_exchange = 'default'
app.conf.task_default_routing_key = 'default'


# Import tasks explicitly to ensure they're registered
import tasks.github_tasks  # noqa

# Additionally, autodiscover tasks
app.autodiscover_tasks(['tasks'])
