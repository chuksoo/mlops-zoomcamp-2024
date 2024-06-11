import requests
import predict

ride = {
    "PULocationID": 10,
    "DOLocationID": 50,
    "trip_distance": 40
}

# features = predict.prepare_features(ride)
# pred = predict.predict(ride)
# print(pred)


url = 'http://localhost:9696/predict'
response = requests.post(url, json=ride)
print(response.json())


