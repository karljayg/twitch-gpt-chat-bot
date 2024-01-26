import requests

def sendMessagetoLlamaModel(msg):

    data = {
        "inputs":   f"### Instruction: {msg} ### Response",
        #"inputs": msg,
        "parameters": {"temperature": 0.7, "repetition_penalty" : 1.15}
    }

    response = requests.post("https://dammmnlbi0.execute-api.ap-southeast-2.amazonaws.com/default/mathison-llama-request", json=data)
    myresponse = response.json()
    print("Response", myresponse)
    return myresponse