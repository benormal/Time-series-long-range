# Deep Spatial-Temporal Graph Modeling

This code is based on an original Graph-WaveNet code ported from [this](https://github.com/sshleifer/Graph-WaveNet).

## Requirements
- python 3
- see `requirements.txt`


## Data Preparation

### Step1: Download METR-LA and PEMS-BAY data from [Google Drive](https://drive.google.com/open?id=10FOTa6HXPqX8Pf5WRoRwcFnW9BrNZEIX) or [Baidu Yun](https://pan.baidu.com/s/14Yy9isAIZYdU__OYEQGa_g) links provided by [DCRNN](https://github.com/liyaguang/DCRNN).

### Step2: Process raw data

```
# Create data directories
mkdir -p data/{METR-LA,PEMS-BAY}

# METR-LA
python generate_training_data.py --output_dir=data/METR-LA --traffic_df_filename=data/metr-la.h5 --hour_interval 1

# PEMS-BAY
python generate_training_data.py --output_dir=data/PEMS-BAY --traffic_df_filename=data/pems-bay.h5 --hour_interval 1
```

### Step3: Graph Construction

```
# Create adj matrix
python -m scripts.gen_adj_mx  --sensor_ids_filename=data/sensor_graph/graph_sensor_ids.txt --normalized_k=0.1\
    --output_pkl_filename=data/sensor_graph/adj_mx.pkl
```

## Train Commands

```
python train.py --gcn_bool --adjtype doubletransition --addaptadj  --randomadj --seq_length 12
```
