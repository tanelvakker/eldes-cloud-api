# eldes-cloud-api
Python module for accessing [Eldes](https://eldesalarms.com/) Cloud API

## Sample usage:

```python
import eldes

client = eldes.EldesClient(username="email",password="password",hostDeviceId="xx", refresh_token_file="refresh_token.txt")
client.is_partition_armed(location="location", partition="partition")
client.get_temperatures(location="location")
```

## General notes
 - If refresh_token_file is not set, username/password login will always be used.
 - hostDeviceId should be random text, but persistent for a single endpoint.
 - Device information gets refreshed once per minute to minimize requests towards API.
 - API will return previous armed/disarmed state when queried right after setting state. You should wait a few seconds before querying the status again.
