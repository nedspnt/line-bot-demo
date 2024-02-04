## Line Chat Bot

#### Deployment in Google Cloud Functions

Run your cloud function while setting your environment variables as follows
```
gcloud functions deploy my-cloud-function \
  --runtime python310 \
  --trigger-http \
  --set-env-vars CHANNEL_ACCESS_TOKEN=your_token,CHANNEL_SECRET=your_secret
```
The environments variables `CHANNEL_ACCESS_TOKEN` and `CHANNEL_SECRET` will be used to authenticate your Line Messaging API.