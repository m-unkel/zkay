# BPL: Blockchain Privacy Language

## Install

### Using Docker

The simplest way to run BPL is using docker. After installing docker, you may
run the docker image by:

```bash
/path/to/bpl-implementation$ ./bpl-docker.sh
(base) root@ae09e165bd19:/bpl-implementation_host$
```

This command mounts directory `bpl-implementation` as `bpl-implementation_host`
within the docker image. Alternatively, you can run `./bpl-docker.sh` from any
other directory `d`, which is then mounted as `d_host`. This allows you to
operate on files of the host, which is important when compiling BPL contracts.

### Directly On Host

Alternatively, you may install BPL on your host directly. To this end, following
the instructions in the [Dockerfile](./install/Dockerfile), marked by: `To
install on host`.

## Unit Tests

To run unit tests, run (example using docker):

```bash
# run docker container
/path/to/bpl-implementation $ ./bpl-docker.sh
# run tests within docker
(base) root@ae09e165bd19:/bpl-implementation_host$ cd src
(base) root@ae09e165bd19:/bpl-implementation_host$ make test
```

## Compile Contracts

To compile a BPL file `test.bpl` and place the output into the current working
directory:

```bash
# run docker container
/path/to/contract$ /path/to/bpl-docker.sh
# run compilation
(base) root@ff2ddb8da49c:/contract_host$ python /bpl-implementation/src/main.py test.bpl
```

## Run Evaluation from CCS 2019

To reproduce the evaluation results from the paper, run the following:

```bash
# run docker container
/path/to/bpl-implementation/eval-ccs2019$ ../bpl-docker.sh
# run evaluation
(base) root@ff2ddb8da49c:/eval-ccs2019_host$ make eval
```
