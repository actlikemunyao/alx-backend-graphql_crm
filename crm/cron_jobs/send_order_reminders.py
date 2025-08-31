#!/usr/bin/env python3
import datetime
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

LOG_FILE = "/tmp/order_reminders_log.txt"

transport = RequestsHTTPTransport(url="http://localhost:8000/graphql", verify=True, retries=3)
client = Client(transport=transport, fetch_schema_from_transport=True)

query = gql("""
query GetRecentOrders {
  orders(last7days: true) {
    id
    customer {
      email
    }
  }
}
""")

def main():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result = client.execute(query)

    with open(LOG_FILE, "a") as f:
        for order in result.get("orders", []):
            f.write(f"{now} - Reminder for Order {order['id']} to {order['customer']['email']}\n")

    print("Order reminders processed!")

if __name__ == "__main__":
    main()
