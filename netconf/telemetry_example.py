from ncclient import manager
import xmltodict
from lxml.etree import fromstring

device = {
    'ip_address': '192.168.1.1',
    'port': '22',
    'username': 'cisco',
    'password': 'cisco',
    'hostkey_verify': False,
    'device_params': {'name': 'csr'}
}

with manager.connect(**device) as m:
    subs = ['/memory-ios-xe-oper:memory-statistics/memory-statistics']
    for sub in subs:
        rpc = f"""
            <establish-subscription xmlns='urn:ietf:params:xml:ns:yang:ietf-event-notifications' xmlns:yp='urn:ietf:params:xml:ns:yang:ietf-yang-push'>
                <stream>yp:yang-push</stream>
                <yp:xpath-filter> {sub} </yp:xpath-filter>
                <yp:period> 500 </yp:period>
            </establish-subscription>
        """

        response = m.dispatch(fromstring(rpc))
        python_resp = xmltodict.parse(response.xml)

        while True:
            sub_data = m.take_notification()
            python_sub_data = xmltodict.parse(sub_data.notification_xml)
            print(f"Sub ID: {python_sub_data['notification']['push_update']['subscription-id']}")
            print(f"Name: {python_sub_data['notification']['push_update']['datastore-contents-xml']['memory-statistics']['memory-statistic'][0]['name']}")
            print(f"Total RAM: {python_sub_data['notification']['push_update']['datastore-contents-xml']['memory-statistics']['memory-statistic'][0]['total-memory']}")
            print(f"Used RAM: {python_sub_data['notification']['push_update']['datastore-contents-xml']['memory-statistics']['memory-statistic'][0]['used-memory']}")
            print(f"Free RAM: {python_sub_data['notification']['push_update']['datastore-contents-xml']['memory-statistics']['memory-statistic'][0]['free-memory']}")
