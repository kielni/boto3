import time

from boto3.sns.utils import subscribe_sqs_queue
from boto3.sqs.utils import convert_queue_url_to_arn
from boto3.utils import json

from tests.integration.base import ConnectionTestCase
from tests import unittest


class SNSConnectionTestCase(ConnectionTestCase, unittest.TestCase):
    service_name = 'sns'
    ops = [
        'add_permission',
        'confirm_subscription',
        'connect_to',
        'create_platform_application',
        'create_platform_endpoint',
        'create_topic',
        'delete_endpoint',
        'delete_platform_application',
        'delete_topic',
        'get_endpoint_attributes',
        'get_platform_application_attributes',
        'get_subscription_attributes',
        'get_topic_attributes',
        'list_endpoints_by_platform_application',
        'list_platform_applications',
        'list_subscriptions',
        'list_subscriptions_by_topic',
        'list_topics',
        'publish',
        'remove_permission',
        'set_endpoint_attributes',
        'set_platform_application_attributes',
        'set_subscription_attributes',
        'set_topic_attributes',
        'subscribe',
        'unsubscribe',
    ]

    def test_integration(self):
        name = 'boto3_lives'
        topic_arn = self.conn.create_topic(
            name=name
        )['TopicArn']

        self.addCleanup(self.conn.delete_topic, topic_arn=topic_arn)

        # FIXME: Needs 100% more waiters.
        time.sleep(5)

        arns = [info['TopicArn'] for info in self.conn.list_topics()['Topics']]
        self.assertTrue(topic_arn in arns)

        # Subscribe first, so we get the notification.
        # To get the notification, we'll create an SQS queue it can deliver to.
        sqs = self.session.connect_to('sqs')
        url = sqs.create_queue(queue_name='boto3_sns_test')['QueueUrl']
        self.addCleanup(sqs.delete_queue, queue_url=url)
        queue_arn = convert_queue_url_to_arn(sqs, url)

        # Run the convenience method to do all the kinda-painful SNS/SQS setup.
        subscribe_sqs_queue(
            self.conn,
            sqs,
            topic_arn,
            url,
            queue_arn
        )

        # Now publish a test message.
        self.conn.publish(
            topic_arn=topic_arn,
            message=json.dumps({
                'default': 'This is a test.'
            })
        )
        time.sleep(5)

        # Ensure the publish succeeded.
        messages = sqs.receive_message(
            queue_url=url
        )
        self.assertTrue(len(messages['Messages']) > 0)
        raw_body = messages['Messages'][0]['Body']
        body = json.loads(raw_body)
        msg = json.loads(body.get('Message', '{}'))
        self.assertEqual(msg, {'default': 'This is a test.'})
