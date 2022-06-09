import init, {client_register_wasm, client_register_finish_wasm, client_login_wasm, client_login_finish_wasm} from "@tiptenbrink/opaquewasm";
import config from "./config";

async function init_opq() {
    // Works in dev, not in prod, for prod just use init()
    //await init("../node_modules/@tiptenbrink/opaquewasm/opaquewasm_bg.wasm");
    await init()
}

export async function clientRegister(username: string, password: string, register_id: string) {
    try {
        await init_opq()
        const { message: message1, state } = client_register_wasm(password)

        console.log(message1)
        console.log(state)

        // get message to server and get message back
        const reqst = {
            "email": username,
            "client_request": message1,
            "registerid": register_id
        }
        const res = await fetch(`${config.auth_location}/register/start/`, {
            method: 'POST', body: JSON.stringify(reqst),
            headers: {
                'Content-Type': 'application/json'
            }
        })
        const parsed = await res.json()
        const server_message = parsed.server_message
        const auth_id = parsed.auth_id
        const register_state = state
        console.log(auth_id)
        console.log(server_message)

        const message2 = client_register_finish_wasm(register_state, server_message)

        console.log(message2)

        const reqst2 = {
            "email": username,
            "client_request": message2,
            "auth_id": auth_id
        }
        const res_finish = await fetch(`${config.auth_location}/register/finish/`, {
            method: 'POST', body: JSON.stringify(reqst2),
            headers: {
                'Content-Type': 'application/json'
            }
        })

        return res_finish.ok

    } catch (e) {
        console.log(e)
        return false
    }
}

export async function clientLogin(username: string, password: string, flow_id: string) {
    try {
        await init_opq()
        const { message: message1, state } = client_login_wasm(password)

        console.log(message1)
        console.log(state)

        // get message to server and get message back
        const reqst = {
            "email": username,
            "client_request": message1
        }
        const res = await fetch(`${config.auth_location}/login/start/`, {
            method: 'POST', body: JSON.stringify(reqst),
            headers: {
                'Content-Type': 'application/json'
            }
        })
        const parsed = await res.json()
        const server_message: string = parsed.server_message
        const auth_id = parsed.auth_id
        const login_state = state
        console.log(auth_id)
        console.log(server_message)

        // pass 'abc'
        //const login_state = "Gg6GSd_2X9ccTkVZBatUyynmRM5CWBVh9j8Fsac2hQAAYoxXlNs3YTKM_4eq-Tr3hOM5TO1OZTaAgI7DYQIV4rhX-EomurCCwcw3cojfbBudPS6aF0YyxJZYbjgD8ABTigIAAMaJ77uRiMGm50uF6_VEFchFlKmwvKhhiUUsRhZhRl1fAEChX0fsJTWoEsS2bPTSt-1BKlRkL85rlA1yZkr56BWbCvhKJrqwgsHMN3KI32wbnT0umhdGMsSWWG44A_AAU4oCYWJj"
        //const server_message = "ho_5N1Kup16z2J_aoR3MxLpxrM--gE-AFLz8-bhkIh_8cilJ2k3wlBxI5tG-aPV_-VNMoit3BFUK-8zO6cYpdAETrMqI8STeP2akP4qAmQ8A5nAFshWJUpU3NfznjqXFTFPMQRJAaV9Ga-xnDUXd7KTkW18gQeoI_QWXN9xgYaFJHsYTVOYXoWKkoOwbHfurl9tNesy7DhgOnFvBH7rxH3-i3Xcl4lPuHtFFlgNCLwR4r1V0wH9tFSGC30LmXpZOBLWWZ0IXIl5BBZ5mSCJJHS9UKiYIYAHjsDjpeMQaRm_0PA70Xqrlk1dLmlhrWSoX46pZQ3Bxp2bKxF38mtr3MQcAAO3RwD2P-EutfATHdQ2W1qQZuJyOjG255FSAsbBLIOFBcpYBCNIitdoxYe7baP6gI_A9LxyK4kP0kOXg17sQ8wQ="
        //const server_message = "GjLrN4JEUsjQgmesadkoPWbOblKFA2B_fbgFclxoW03GVBmt60hTg5I8TzpcuB6VAZffJkgztbfI5pETN-l-WAHbuTdN1azA6NI6d-oP3TOm-_sVanwq2zE35LJAMHhXQDdLpf3YxY3OCZfMCDfjz4hC8yU9KR4kawwKnnVj8cI_DjUG2M7pFJAR5VJ1j5yYmERTn_8S_vzxm6M6y0FGARx_J8HcjATeNkdiS9DCtte-1vCZa0UnhOpOf4IEEHl3AJ71NBsDbp8kEI4GanzhH3bPCqoWukPT_MToVe1pbROJkCKaxKwBu1PuMbF4e-hw4EtQuCJmb5l6-Zm7SkowBVYAAPfgo_zRAhkBivXxX0t0H33plYrN_7yKaDZIZiCMMyiuYabsvs_op4JKgD2hV-X1PPpUdrMZ-WVrZstLRiqr2_E="

        const { message: message2, session } = client_login_finish_wasm(login_state, server_message)

        console.log(message2)

        const reqst2 = {
            "email": username,
            "client_request": message2,
            "auth_id": auth_id,
            "flow_id": flow_id
        }
        const res2 = await fetch(`${config.auth_location}/login/finish/`, {
            method: 'POST', body: JSON.stringify(reqst2),
            headers: {
                'Content-Type': 'application/json'
            }
        })

        if (res2.ok) {
            return session
        }
        return null

    } catch (e) {
        if (e instanceof Error && e.name === "InvalidLogin") {
            console.log("IsError")
            console.log(e.message)
        }
        else {
            console.log(e)
        }
        return null
    }
}

export function binToBase64Url(byte_array: Uint8Array) {
    const random_chrpts = Array.from(byte_array).map((num) => {
        return String.fromCharCode(num)
    }).join('')
    return btoa(random_chrpts)
        .replaceAll("/", "_").replaceAll("+", "-")
        .replaceAll("=", "")
}

export function base64ToBin(encoded_string: string) {
    const base64 = encoded_string.replaceAll("_", "/").replaceAll("-", "+");
    const decoded = atob(base64)
    return new Uint8Array(Array.from(decoded).map((char) => {
        return char.charCodeAt(0)
    }))
}

export async function keys() {
    const keyPair = await window.crypto.subtle.generateKey(
        {
            name: "RSA-OAEP",
            modulusLength: 4096,
            publicExponent: new Uint8Array([1, 0, 1]),
            hash: "SHA-256"
        },
        true,
        ["encrypt", "decrypt"]
    );
    if (!keyPair.privateKey) {
        throw Error
    }
    const exported_private = await window.crypto.subtle.exportKey(
        "pkcs8",
        keyPair.privateKey
    );

    if (!keyPair.publicKey) {
        throw Error
    }
    const exported_public = await window.crypto.subtle.exportKey(
        "spki",
        keyPair.publicKey
    );

    return {
        "private_key": binToBase64Url(new Uint8Array(exported_private)),
        "public_key": binToBase64Url(new Uint8Array(exported_public))
    }
}

export async function decryptPass(private_key_str: string, encrypted_pass: string) {
    const private_bytes = base64ToBin(private_key_str)

    const private_key = await window.crypto.subtle.importKey(
        "pkcs8",
        private_bytes,
        {
            name: "RSA-OAEP",
            hash: "SHA-256"
        },
        true,
        ["decrypt"]
    );

    const encrypted_pass_bytes = base64ToBin(encrypted_pass)

    const pass_bytes = await window.crypto.subtle.decrypt(
        {
            name: "RSA-OAEP"
        },
        private_key,
        encrypted_pass_bytes
    );

    let enc = new TextDecoder();
    return enc.decode(pass_bytes);
}