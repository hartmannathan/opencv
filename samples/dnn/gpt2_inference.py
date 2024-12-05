'''
This is a sample script to run GPT-2 inference in OpenCV using ONNX model.
The script loads the GPT-2 model and runs inference on a given prompt.
Currently script only works with fixed size window, that means
you will have to specify prompt of the same length as when model was exported to ONNX.


Exporting GPT-2 model to ONNX.
To export GPT-2 model to ONNX, you can use the following procedure:

1. Clone fork of Andrej Karpathy's GPT-2 repository:

    git clone -b ash/export-gpt2-onnx-dynamic https://github.com/Abdurrahheem/build-nanogpt.git

2. Install the required dependencies:

    pip install -r requirements.txt

3  Export the model to ONNX:

    python export2onnx.py --promt=<Any-promt-you-want>


Run the script:
1. Install the required dependencies:

    pip install tiktoken==0.7.0 numpy tqdm

2. Run the script:
    python gpt2_inference.py --model=<path-to-onnx-model>  --prompt=<use-promt-of-the-same-length-used-while-exporting>
'''



import numpy as np
import tiktoken
import argparse
import cv2 as cv
from tqdm import tqdm

def parse_args():
    parser = argparse.ArgumentParser(description='Use this script to run GPT-2 inference in OpenCV',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--model', type=str, required=True, help='Path to GPT-2 model ONNX model file.')
    parser.add_argument("--prompt", type=str, default="Hello, I'm a language model,", help="Prompt to start with.")
    parser.add_argument("--max_seq_len", type=int, default=40, help="Number of tokens to continue.")
    parser.add_argument("--batch_size", type=int, default=1, help="Number of batches.")
    parser.add_argument("--seed", type=int, default=0, help="Random seed")
    return parser.parse_args()

def stable_softmax(logits):
    exp_logits = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
    return exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)


def gpt2_inference(net, tokens, max_length, num_return_sequences=1):

    print("Inferencing GPT-2 model...")
    x = np.array(tokens)
    x = np.tile(x, (num_return_sequences, 1)).astype(np.int32)
    pos = np.arange(0, len(x), dtype=np.int32)

    counter = x.shape[1]
    pbar = tqdm(total=max_length - counter, desc="Generating tokens")
    while counter < max_length:

        net.setInputsNames(['input_ids', 'position_ids'])
        net.setInput(x, 'input_ids')
        net.setInput(pos, 'position_ids')

        logits = net.forward()

        # logits is assumed to be (B, seq_length, vocab_size) and needs to be the last token's logits
        logits = logits[:, -1, :]  # (B, vocab_size)

        # Get the probabilities using softmax
        probs = stable_softmax(logits)

        # Do top-k sampling of 50
        topk_indices = np.argpartition(probs, -50, axis=-1)[:, -50:]
        topk_probs = np.take_along_axis(probs, topk_indices, axis=-1)

        # Normalize top-k probabilities
        topk_probs /= np.sum(topk_probs, axis=-1, keepdims=True)

        # Select a token from the top-k probabilities
        sampled_indices = [np.random.choice(topk_indices[i], p=topk_probs[i]) for i in range(len(topk_probs))]
        sampled_indices = np.array(sampled_indices).reshape(-1, 1)

        # Append to the sequence
        x = np.concatenate((x, sampled_indices), axis=1)
        pos = np.arange(0, x.shape[1], dtype=np.int32) # shape (T)

        counter += 1
        pbar.update(1)

    pbar.close()
    print("Inference done!")
    return x

if __name__ == '__main__':

    args = parse_args()
    np.random.seed(args.seed)
    max_length = args.max_seq_len
    num_return_sequences = args.batch_size
    prompt = args.prompt

    net = cv.dnn.readNet(args.model)

    enc = tiktoken.get_encoding('gpt2')
    tokens = enc.encode(prompt)

    output = gpt2_inference(net, tokens, max_length, num_return_sequences)

    for i in range(num_return_sequences):
        tokens = output[i].tolist()
        decoded = enc.decode(tokens)
        print(">>>>", decoded)