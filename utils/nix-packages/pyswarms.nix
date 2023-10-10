{ lib, buildPythonPackage, fetchPypi, numpy, matplotlib, scipy, tqdm, attrs }:

buildPythonPackage rec {
  pname = "pyswarms";
  version = "1.3.0"; # Revisa PyPi para la versión más reciente

  src = fetchPypi {
    inherit pname version;
    sha256 = "sha256-EgSqnDMsZiET48N9GxCZBvSghZsp3tgMFYLcZjh840s="; # Este valor debe ser corregido
  };

  propagatedBuildInputs = [ numpy matplotlib scipy tqdm attrs ];

  # Los tests pueden requerir dependencias adicionales o ser desactivados si causan problemas
  doCheck = false;

  meta = with lib; {
    description = "Particle swarm optimization (PSO) with python";
    homepage = "https://pypi.org/project/pyswarms/";
    license = licenses.mit;
    maintainers = with maintainers; [ ]; # Aquí puedes agregar tu nombre de usuario de maintainer
  };
}
