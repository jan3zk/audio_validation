# For Linux executable run:
```
pyinstaller -y audio_validation.py --hidden-import='PIL._tkinter_finder' --collect-data librosa --hidden-import='sklearn.neighbors._partition_nodes'
```
```
ln -s dist/audio_validation/audio_validation audio_validation
```

# For Windows executable run:
```
pyinstaller -y -c audio_validation.py --collect-data librosa --hidden-import='sklearn.neighbors._partition_nodes' --hidden-import='sklearn.utils._weight_vector'
```
