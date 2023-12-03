import {client_register_wasm, client_register_finish_wasm, client_login_wasm, client_login_finish_wasm} from "@tiptenbrink/opaquewasm";
import config from "../config";
import {RegisterState} from "../credentials/register/Register";
import {back_post, catch_api} from "./api";
import {z} from "zod";

const OpaqueResponse = z.object({
    server_message: z.string(),
    auth_id: z.string()
})

export async function clientRegister(registerState: RegisterState) {
    try {
        const { message: message1, state: register_state } = client_register_wasm(registerState.password)

        const register_start = {
            "email": registerState.email,
            "client_request": message1,
            "register_id": registerState.register_id
        }
        const res = await back_post("onboard/register/", register_start)
        const {server_message, auth_id} = OpaqueResponse.parse(res)

        const message2 = client_register_finish_wasm(register_state, registerState.password, server_message)
 
        const register_finish = {
            "email": registerState.email,
            "client_request": message2,
            "auth_id": auth_id,
            "register_id": registerState.register_id,
            "callname": registerState.callname,
            eduinstitution: registerState.eduinstitution,
            birthdate: registerState.date_of_birth,
            age_privacy: registerState.birthday_check
        }
        await back_post("onboard/finish/", register_finish)
        return true

    } catch (e) {
        console.log(e)
        return false
    }
}

export async function passUpdate(email: string, flow_id: string, password: string) {
    try {
        const { message: message1, state: register_state } = client_register_wasm(password)

        const register_start = {
            "email": email,
            "client_request": message1,
            "flow_id": flow_id
        }
        const res = await back_post("update/password/start/", register_start)
        const {server_message, auth_id} = OpaqueResponse.parse(res)

        const message2 = client_register_finish_wasm(register_state, password, server_message)

        const register_finish = {
            "client_request": message2,
            "auth_id": auth_id,
        }

        await back_post("update/password/finish/", register_finish)
        return true

    } catch (e) {
        console.log(e)
        return false
    }
}

export async function clientLogin(username: string, password: string, flow_id: string) {
    try {
        const { message: message1, state: login_state } = client_login_wasm(password)

        // get message to server and get message back
        const login_start = {
            "email": username,
            "client_request": message1
        }
        const res = await back_post("login/start/", login_start)
        const {server_message, auth_id} = OpaqueResponse.parse(res)

        // pass 'abc'
        //const login_state = "Gg6GSd_2X9ccTkVZBatUyynmRM5CWBVh9j8Fsac2hQAAYoxXlNs3YTKM_4eq-Tr3hOM5TO1OZTaAgI7DYQIV4rhX-EomurCCwcw3cojfbBudPS6aF0YyxJZYbjgD8ABTigIAAMaJ77uRiMGm50uF6_VEFchFlKmwvKhhiUUsRhZhRl1fAEChX0fsJTWoEsS2bPTSt-1BKlRkL85rlA1yZkr56BWbCvhKJrqwgsHMN3KI32wbnT0umhdGMsSWWG44A_AAU4oCYWJj"
        //const server_message = "ho_5N1Kup16z2J_aoR3MxLpxrM--gE-AFLz8-bhkIh_8cilJ2k3wlBxI5tG-aPV_-VNMoit3BFUK-8zO6cYpdAETrMqI8STeP2akP4qAmQ8A5nAFshWJUpU3NfznjqXFTFPMQRJAaV9Ga-xnDUXd7KTkW18gQeoI_QWXN9xgYaFJHsYTVOYXoWKkoOwbHfurl9tNesy7DhgOnFvBH7rxH3-i3Xcl4lPuHtFFlgNCLwR4r1V0wH9tFSGC30LmXpZOBLWWZ0IXIl5BBZ5mSCJJHS9UKiYIYAHjsDjpeMQaRm_0PA70Xqrlk1dLmlhrWSoX46pZQ3Bxp2bKxF38mtr3MQcAAO3RwD2P-EutfATHdQ2W1qQZuJyOjG255FSAsbBLIOFBcpYBCNIitdoxYe7baP6gI_A9LxyK4kP0kOXg17sQ8wQ="
        //const server_message = "GjLrN4JEUsjQgmesadkoPWbOblKFA2B_fbgFclxoW03GVBmt60hTg5I8TzpcuB6VAZffJkgztbfI5pETN-l-WAHbuTdN1azA6NI6d-oP3TOm-_sVanwq2zE35LJAMHhXQDdLpf3YxY3OCZfMCDfjz4hC8yU9KR4kawwKnnVj8cI_DjUG2M7pFJAR5VJ1j5yYmERTn_8S_vzxm6M6y0FGARx_J8HcjATeNkdiS9DCtte-1vCZa0UnhOpOf4IEEHl3AJ71NBsDbp8kEI4GanzhH3bPCqoWukPT_MToVe1pbROJkCKaxKwBu1PuMbF4e-hw4EtQuCJmb5l6-Zm7SkowBVYAAPfgo_zRAhkBivXxX0t0H33plYrN_7yKaDZIZiCMMyiuYabsvs_op4JKgD2hV-X1PPpUdrMZ-WVrZstLRiqr2_E="

        const { message: message2, session } = client_login_finish_wasm(login_state, password, server_message)

        const login_finish = {
            "email": username,
            "client_request": message2,
            "auth_id": auth_id,
            "flow_id": flow_id
        }

        await back_post("login/finish/", login_finish)
        return session

    } catch (e) {
        if (e instanceof Error && e.name === "InvalidLogin") {
            console.log("IsError")
            console.log(e.message)
        }
        else {
            const err = catch_api(e)
            console.log(err)
        }
        return null
    }
}