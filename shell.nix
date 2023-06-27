{ kapack ? import
    ( fetchTarball "https://github.com/oar-team/nur-kapack/archive/master.tar.gz")
  {}
}:

with kapack.pkgs;

let
  self = rec {
    experiment_env = mkShell rec {
      name = "experiment_env";
      buildInputs = [
        kapack.batsim
        kapack.batsched
        kapack.pybatsim
        kapack.batexpe
      ];
    };
  };
in
  self.experiment_env
