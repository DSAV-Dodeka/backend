import config from "./config"
import ky, {HTTPError, ResponsePromise} from "ky"
import {z} from "zod";

const api = ky.create({prefixUrl: config.auth_location});

export const back_post = async (endpoint: string, json: Object) => {
    return await api.post(endpoint, {json: json}).json()
}

const ReturnedError = z.object({
    error: z.string(),
    error_description: z.string(),
    debug_key: z.string().optional()
})
type ApiError = {
    code: number,
    error: string
    error_description: string
    debug_key?: string
}

export const catch_api = async (e: unknown): Promise<ApiError> => {
    if (e instanceof HTTPError) {
        const err_json = await e.response.json()
        return { ...ReturnedError.parse(err_json), code: e.response.status }
    } else {
        throw e
    }
}