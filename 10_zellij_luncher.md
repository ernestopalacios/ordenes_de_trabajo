# Como crear un lanzador de microservicios en Zellij

1. Asegurarse de que 'zookepper/kafka' se encuentr corriendo en Docker
2. Tener instalado Zellij
3. Agregar la función en `/.config/fish/config.fish`:

```
# Definido en /home/vlad/.config/fish/config.fish @ línea 11
function ot
    # Opens a new Kitty tab and launches Zellij with the layout
    # --new-tab: creates the tab
    # --tab-title: gives it a clear name in Kitty
    # zellij --layout work: the command to run in that new tab
    kitty @ launch --type=tab --tab-title "Ordenes" zellij --layout work
end
```

4. Crear un nuevo archivo: `~/.config/zellij/layouts/work.kdl`

```kdl
layout {
    default_tab_template {
        pane size=1 borderless=true {
            plugin location="zellij:tab-bar"
        }
        children
        pane size=2 borderless=true {
            plugin location="zellij:status-bar"
        }
    }

    tab name="Ordenes de Trabajo" {
        // Pane 1: Producer
        pane cwd="/home/vlad/GIT/ot_he_v30_estable" name="Producer" {
            command "fish"
            args "-c" "source .venv/bin/activate.fish; python 01_producer.py '/home/vlad/Documentos/_gestion_ot/'; exec fish"
        }

        // Pane 2: Consumer
        pane cwd="/home/vlad/GIT/ot_he_v30_estable" name="Consumer" {
            command "fish"
            args "-c" "source .venv/bin/activate.fish; python 02_consumer.py; exec fish"
        }

        // Pane 3: Concat
        pane cwd="/home/vlad/GIT/ot_he_v30_estable" name="Concat" {
            command "fish"
            args "-c" "source .venv/bin/activate.fish; python 03_concat_ot.py; exec fish"
        }
    }
}
```
