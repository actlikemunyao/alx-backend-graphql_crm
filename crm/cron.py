import datetime
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

def log_crm_heartbeat():
    now = datetime.datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    with open("/tmp/crm_heartbeat_log.txt", "a") as f:
        f.write(f"{now} CRM is alive\n")

def update_low_stock():
    transport = RequestsHTTPTransport(url="http://localhost:8000/graphql", verify=True, retries=3)
    client = Client(transport=transport, fetch_schema_from_transport=True)

    mutation = gql("""
    mutation {
      updateLowStockProducts {
        success
        updatedProducts {
          name
          stock
        }
      }
    }
    """)

    result = client.execute(mutation)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open("/tmp/low_stock_updates_log.txt", "a") as f:
        for p in result["updateLowStockProducts"]["updatedProducts"]:
            f.write(f"{now} - Updated {p['name']} to stock {p['stock']}\n")
