# JEV GETTING STARTED
## Background
- This project will help evaluate the capabilities of the new AI Model JEV
- Jev is not a typical LLM, and only a Classification Model 
- Jev defines a set of AI primitives such as "State", "Choices", "NOUL" and "Score"
- More info about Jev can be found here: https://docs.typesafe.ai/introduction
## How to Access Jev
- Jev is accessible via API and the service provider we will use is opencode.ai 
- The name of the model for Jev in opencode.ai is "jev-1.13"
- This model can be accessed using opencode.ai API methods and the name provided above
- More info about the opencode.ai zen models can be found here: https://opencode.ai/zen
## Programming languages and tools 
- Use Python 3.x for backend code
  - Use FastAPI or similar 
  - Use uv as package manager 
- Use Reactjs or similar frontend programming langauge and libraries
## What to build 
### Functional Requirements
- A webpage that will allow user to type a classification question such as classify a customer query for various metrics 
  - e.g. "I have been billed twice for the subscription and I want to review the charge and reverse it asap"
  - Metrics such as "intent", "urgency", "handling department"
- Then, the Jev API is invoked with the necessary JSON object and the response is retrieved and displayed on the same webpage
- The webpage will also show the cost for the request and the time it took to process the request
### Non Functional Requirements
- Log the requests and responses into a log file (e.g. log.md, log.txt or similar) and save the log file at the root of the project
- Identify cost and latency metrics and save the cost and latency for each request and response pair along with the logs
