import sgreplay_pb2
import google.protobuf.message

# Load the binary data
path_to_your_file = r'C:\Users\karl_\AppData\Local\Stormgate\Saved\Replays\7a2ddb7b-4ad7-4274-96d2-0e2b5855f09c'
header_size = 16  # Assuming the first 16 bytes are non-protobuf data

# Then proceed with opening the file as before
with open(path_to_your_file + r'\CL44821-2024.02.07-16.55.SGReplay', 'rb') as file:
    file.seek(header_size)  # Skip the header
    data = file.read()

# Parse the data
replay_data = sgreplay_pb2.ReplayStreamRecordHeader()
try:
    replay_data.ParseFromString(data)
except google.protobuf.message.DecodeError:
    print("Error: Unable to parse the data. Please ensure the data matches the protobuf message definition.")

# Access and work with the parsed data
print(replay_data)