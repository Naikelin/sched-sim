{ kapack ? import
    (fetchTarball {
      url = "https://github.com/oar-team/nur-kapack/archive/8c2f3d907db117229fa11c95c9342f9026daf9c2.tar.gz";
      # Asegúrate de obtener y usar la SHA256 correcta para este commit
      sha256 = "0n53jj3kw1vcs2x08a3sad744c3j1699d3z0nkbzljhgyhwh8li0";
    })
  {}
}:

with kapack.pkgs;

let
  self = rec {
    experiment_env = mkShell rec {
      name = "experiment_env";
      buildInputs = [
        kapack.simgrid
        kapack.batsim
        kapack.batsched
        kapack.pybatsim
        kapack.batexpe
      ];
      shellHook = ''
        export PYTHONPATH=$PYTHONPATH:${kapack.pybatsim}/lib/python3.10/site-packages
      '';
    };
  };
in
  self.experiment_env