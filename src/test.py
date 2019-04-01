from influxdb import InfluxDBClient

db_client = InfluxDBClient("influxdb", 8086, "admin", "password", "lianjia")
# db_client.create_database("lianjia")

result = db_client.query("select id,deal_price,listing_price,transaction_cycle from deal_price;")

# print(result)
print(dir(result))
for item in result.get_points():
    print(item)
