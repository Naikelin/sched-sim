#!/bin/bash

if [ "$#" -ne 4 ]; then
    echo "Uso: $0 <nombre_plataforma> <ruta_carga_trabajo> <directorio_salida> <nombres_simulaciones_separados_por_coma>"
    exit 1
fi

PLATFORM_NAME=$1
WORKLOAD_PATH=$2
OUTPUT_DIR=$3
SCHEDULER_NAMES_STRING=$4

IFS=',' read -r -a SCHEDULER_NAMES_ARRAY <<< "$SCHEDULER_NAMES_STRING"

echo "Plataforma: $PLATFORM_NAME"
echo "Carga de trabajo: $WORKLOAD_PATH"
echo "Directorio de salida: $OUTPUT_DIR"
echo "Nombres de simulaciones: ${SCHEDULER_NAMES_ARRAY[@]}"
echo ""

if [ ! -f "platforms/$PLATFORM_NAME" ]; then
    echo "Error: La ruta de la plataforma no existe: $PLATFORM_NAME"
    exit 1
fi

if [ ! -f "workloads/$WORKLOAD_PATH" ]; then
    echo "Error: La ruta de la carga de trabajo no existe: $WORKLOAD_PATH"
    exit 1
fi

if [ ! -d "$OUTPUT_DIR" ]; then
    echo "El directorio de salida no existe, intentando crearlo: $OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"
    if [ $? -ne 0 ]; then
        echo "Error al crear el directorio de salida: $OUTPUT_DIR"
        exit 1
    fi
fi

for SCHEDULER_NAME in "${SCHEDULER_NAMES_ARRAY[@]}"; do
    echo "Simulando: $SCHEDULER_NAME"

    CONFIG_TEMPLATE="schedulers/template.yaml"
    CONFIG_FILE="schedulers/${SCHEDULER_NAME}.yaml"

    if [ ! -f "$CONFIG_TEMPLATE" ]; then
        echo "Error: El archivo de plantilla no existe: $CONFIG_TEMPLATE"
        continue 
    fi

    sed "s|{PLATFORM_NAME}|$PLATFORM_NAME|g" "$CONFIG_TEMPLATE" | \
    sed "s|{WORKLOAD_PATH}|$WORKLOAD_PATH|g" | \
    sed "s|{OUTPUT_DIR}|$OUTPUT_DIR|g" | \
    sed "s|{SIMULATION_NAME}|$SCHEDULER_NAME|g" > "$CONFIG_FILE"

    START_TIME=$(date +%s)

    docker run --rm -v "$(pwd)":/sched-sim tanaxer/pybatsim robin schedulers/$SCHEDULER_NAME.yaml
    if [ $? -ne 0 ]; then
        echo "Error al simular: $SCHEDULER_NAME"
        exit 1
    fi

    END_TIME=$(date +%s)
    ELAPSED_TIME=$((END_TIME - START_TIME))

    echo "Simulación terminada: $SCHEDULER_NAME"
    echo "Tiempo de ejecución: $ELAPSED_TIME segundos"
    echo ""
done

