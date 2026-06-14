import time
import torch
from torchvision import transforms as T

# 🔥 MUST match training normalization
transform = T.Compose([
    T.ToTensor(),
    T.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

def run_inference(model, image, device):
    """
    image: RGB numpy array (H, W, 3)
    """
    tensor = transform(image).unsqueeze(0).to(device)

    start = time.time()
    with torch.no_grad():
        pred = model(tensor)
        prob = torch.sigmoid(pred)
    end = time.time()

    return prob.squeeze().cpu().numpy(), round(end - start, 3)
