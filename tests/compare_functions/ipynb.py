def cuenta_to_dict(valor):
    if pd.isna(valor) or valor == "":
        return []
    
    elementos = str(valor).split(", ")
    resultado = []
    
    for item in elementos:
        if ":" in item:
            # Split "REDES:30" -> key: "REDES", value: 30
            key, val = item.rsplit(":", 1)
            resultado.append({"cuenta": key.strip(), "peso": float(val) / 100})
        else:
            # No ":" found, assume 100% (1.0)
            resultado.append({"cuenta": item.strip(), "peso": 1.0})
            
    return resultado


def dict_to_cuenta(lista):
    if not lista or (isinstance(lista, float) and pd.isna(lista)):
        return ""
    
    elementos = []
    
    for item in lista:
        cuenta = item["cuenta"].strip()
        peso = item["peso"]
        
        if peso == 1.0:
            # No ":" needed, just the account name
            elementos.append(cuenta)
        else:
            # Convert back: 0.30 -> 30, format as "CUENTA:30"
            valor = int(round(peso * 100))
            elementos.append(f"{cuenta}:{valor}")
    
    return ", ".join(elementos)
