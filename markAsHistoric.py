'''
Marks nodes as historical for an AppDynamics application

Usage: python marknodeshistorical.py [options]

Options:
  -h, --help                     show this help
  -c ..., --controllerURL=...    controller URL
  -n ..., --userName=...         user name
  -p ..., --userPassword=...     user password
  -a ..., --application=...      application
'''

import getopt
import requests
import json
import sys


def usage():
    print
    __doc__


def main(argv):
    controllerURL = 'http://yourcontroller:8090'
    userName = 'youruser@customer1'
    userPassword = 'yourpassword'
    application = 'yourapplication'

    try:
        opts, args = getopt.getopt(argv, "hc:n:p:a:",
                                   ["help", "controllerURL=", "userName=", "userPassword=", "application="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-c", "--controllerURL"):
            controllerURL = arg
        elif opt in ("-n", "--userName"):
            userName = arg
        elif opt in ("-p", "--userPassword"):
            userPassword = arg
        elif opt in ("-a", "--application"):
            application = arg
    if not (controllerURL and userName and userPassword and application):
        usage()
        sys.exit(2)

    print('connecting to '+str(controllerURL))

    resp = requests.get(controllerURL + '/controller/rest/applications/' + application + '/nodes?output=JSON',
                        auth=(userName, userPassword), verify=True, timeout=60)
    if (resp.ok):
        nodeList = json.loads(resp.content)
        nodeIds=[]
        for node in nodeList:
            metricPath = 'Application Infrastructure Performance|' + node['tierName'] + '|Individual Nodes|' + node[
                'name'] + '|Agent|*|Availability'
            try:
                elementCount=0
                appAvail=0
                machineAvail=0
                aresp = requests.get(
                    controllerURL + '/controller/rest/applications/' + application + '/metric-data?metric-path=' + metricPath + '&time-range-type=BEFORE_NOW&duration-in-mins=5&output=JSON&rollup=true',
                    auth=(userName, userPassword), verify=True, timeout=10)
                if (aresp.ok):
                    metrics = json.loads(aresp.content)
                    for item in metrics:
                        element = metrics[elementCount]
                        metric_values = element['metricValues']
                        for mitem in metric_values:
                            if element['metricName'] == 'Agent|App|Availability':
                                appAvail = element['metricValues'][0]['sum']
                            if element['metricName'] == 'Agent|Machine|Availability':
                                machineAvail = element['metricValues'][0]['sum']
                        elementCount += 1

                    #If both the app agent and machine agent are not available store the id for marking
                    if (appAvail == 0 or appAvail is None) and (machineAvail == 0 or machineAvail is None):
                        nodeIds.append(str(node['id']))
            except:
                print(node['name'] + ' exception checking availability')
                pass
    else:
        print(resp.raise_for_status())
    # Now delete all the relevant nodes
    if len(nodeIds) > 0:
        try:
            list(filter((None).__ne__, nodeIds))
            nodeString = ",".join(map(str, nodeIds))
            print('Marking the following nodes as historic: ' + nodeString)
            hresp = requests.post(controllerURL + '/controller/rest/mark-nodes-historical?application-component-node-ids='+nodeString,
                                  auth=(userName, userPassword), verify=True,
                                  timeout=10)
            print("Marked "+str(len(nodeIds))+" as historic")
        except Exception as e:
            print('Exception occurred marking nodes as historic! ' + str(e))
    else:
        print("No nodes to remove")

    print("End of process...")
if __name__ == "__main__":
    main(sys.argv[1:])

