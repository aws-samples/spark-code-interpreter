#!/bin/bash
set -e

# Update and upgrade system
sudo dnf update && sudo dnf upgrade -y
sudo yum groupinstall "Development Tools" -y
sudo yum install libffi-devel bzip2-devel -y
sudo yum install python-pip -y
sudo yum install tmux git -y 
# sudo yum install libffi-dev libssl-dev tmux git build-essential -y 
# textract installtion pre-requisites
# https://textract.readthedocs.io/en/stable/installation.html#ubuntu-debian
# sudo yum install libxml2-dev libxslt1-dev antiword unrtf poppler-utils tesseract-ocr flac ffmpeg lame libmad0 libsox-fmt-mp3 sox libjpeg-dev swig -y


# Optionally install Tesseract-OCR; if it fails, log the error and continue.
# yum install -y tesseract-ocr-all || echo "Optional dependency tesseract-ocr-all installation failed, continuing..."

# Clone the Git repository into a folder named Bluebear
cd ~/
echo "Cloning repo ${git_repo}"
git clone -b ${git_branch} ${git_repo} bluebear
cd bluebear

# Install Python dependencies
mkdir .venv
sudo chmod 777 .venv
python3 -m venv .venv
cd .venv/bin
source activate
cd ../..
pip install -r req.txt
aws configure set region ${aws_region}
sed -i -e "s/{{ACCOUNT_ID}}/${aws_account_id}/g" config.json
sed -i -e "s/{{REGION}}/${aws_region}/g" config.json


# Start the Bluebear Streamlit app in a tmux session with logging
tmux new -d -s mysession "python3 -m streamlit run bedrock-chat.py 2>&1 | tee /root/bluebear/streamlit.log"

echo "Setup complete. Use 'tmux attach -t mysession' to view the session."