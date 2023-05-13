# MacOs

## Installing PyQt5 on M1 (arm)

### Installing through brew

```shell
> brew install pyqt@5
```

### Pip install

It might be possible to install pyqt5 using `pip`.
Try with `pip insall pyqt5 --verbose` and if you see that it's stack at asking for license, then use the following command to silently accept it

```shell
> pip install pyqt5 --verbose --config-settings --confirm-license=
```


