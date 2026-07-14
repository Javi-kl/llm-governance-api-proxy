{
  description = "llm-governance-api-proxy";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
    in {
      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [
          python314                            
          ruff                                 
          basedpyright                         
          pre-commit
        ];

        
        LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
          pkgs.stdenv.cc.cc.lib
        ];
        
        shellHook = ''
          echo "🐍 $(python --version) | ruff $(ruff --version | cut -d' ' -f2) | basedpyright $(basedpyright --version)"
        '';
      };
    };
}

