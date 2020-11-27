import boto3
import xmltodict
import json

def getResults(item):
    # Get the status of the HIT
    hit = client.get_hit(HITId=item['hit_id'])
    item['status'] = hit['HIT']['HITStatus']
    # Get a list of the Assignments that have been submitted
    assignmentsList = client.list_assignments_for_hit(
        HITId=item['hit_id'],
        AssignmentStatuses=['Submitted', 'Approved'],
        MaxResults=10
    )
    assignments = assignmentsList['Assignments']
    item['assignments_submitted_count'] = len(assignments)
    answers = []
    for assignment in assignments:

        # Retreive the attributes for each Assignment
        worker_id = assignment['WorkerId']
        assignment_id = assignment['AssignmentId']

        # Retrieve the value submitted by the Worker from the XML
        answer_dict = xmltodict.parse(assignment['Answer'])
        answer = answer_dict['QuestionFormAnswers']['Answer']['FreeText']
        answers.append(int(answer))

        # Approve the Assignment (if it hasn't been already)
        if assignment['AssignmentStatus'] == 'Submitted':
            client.approve_assignment(
                AssignmentId=assignment_id,
                OverrideRejection=False
            )

    # Add the answers that have been retrieved for this item
    item['answers'] = answers
    if len(answers) > 0:
        item['avg_answer'] = sum(answers) / len(answers)


create_hits_in_production = False
environments = {
  "production": {
    "endpoint": "https://mturk-requester.us-east-1.amazonaws.com",
    "preview": "https://www.mturk.com/mturk/preview"
  },
  "sandbox": {
    "endpoint":
          "https://mturk-requester-sandbox.us-east-1.amazonaws.com",
    "preview": "https://workersandbox.mturk.com/mturk/preview"
  },
}
mturk_environment = environments["production"] if create_hits_in_production else environments["sandbox"]
session = boto3.Session(profile_name='mturk')
client = session.client(
    service_name='mturk',
    region_name='us-east-1',
    endpoint_url=mturk_environment['endpoint'],
)

print(client.get_account_balance()['AvailableBalance'])


tweets = ['in science class right now... urgh... stupid project..',
          'hmmm what to have for breaky?... Honey on toast ',
          'Doing home work  x',
          'Headed out of town for a few days. Will miss my girls']


html_layout = open('./SentimentQuestion.html', 'r').read()
QUESTION_XML = """<HTMLQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2011-11-11/HTMLQuestion.xsd">
        <HTMLContent><![CDATA[{}]]></HTMLContent>
        <FrameHeight>650</FrameHeight>
        </HTMLQuestion>"""
question_xml = QUESTION_XML.format(html_layout)

TaskAttributes = {
    'MaxAssignments': 5,
    # How long the task will be available on MTurk (1 hour)
    'LifetimeInSeconds': 60*60,
    # How long Workers have to complete each item (10 minutes)
    'AssignmentDurationInSeconds': 60*10,
    # The reward you will offer Workers for each response
    'Reward': '0.05',
    'Title': 'Please Provide sentiment for a Tweet',    # set different group by title
    'Keywords': 'sentiment, tweet',
    'Description': 'Rate the sentiment of a tweet on a scale of 1 to 10.'
}

results = []
hit_type_id = ''
for tweet in tweets:
    response = client.create_hit(
        **TaskAttributes,
        Question=question_xml.replace('${content}', tweet)
    )
    hit_type_id = response['HIT']['HITTypeId']
    results.append({
        'tweet': tweet,
        'hit_id': response['HIT']['HITId']
    })
    print(mturk_environment['preview'] + "?groupId={}".format(hit_type_id))
    while False:    # It needs several seconds to obtain the results
        item = results[-1]
        getResults(item)
        if len(item['answers']) != 0:
            print("finished！")
            break


print("You can view the HITs here:")
print(mturk_environment['preview'] + "?groupId={}".format(hit_type_id))


for item in results:
    getResults(item)

print(json.dumps(results, indent=2))

# response = client.create_hit(
#     **TaskAttributes,
#     Question=question_xml.replace('${content}', " ".join(results))
# )
# hit_type_id = response['HIT']['HITTypeId']
