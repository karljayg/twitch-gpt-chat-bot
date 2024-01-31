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

    if isinstance(myresponse, list):
        # Response is a list of dictionaries
        if myresponse:
            response_string = myresponse[0]['generated_text'].split("### Response")[-1].strip().strip('\"')
        else:
            print("No response found in the list.")
    elif isinstance(myresponse, dict):
        # Response is a single dictionary
        if 'outputs' in myresponse and 'text' in myresponse['outputs']:
            if myresponse['outputs']['text']:
                response_string = myresponse['outputs']['text'][0].split("### Response")[-1].strip().strip('\"')
            else:
                print("No text found in the response.")
        else:
            print("Invalid response format.")
    else:
        print("Unexpected response type:", type(myresponse))

    return response_string