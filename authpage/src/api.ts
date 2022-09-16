import config from "./config"
import ky, {HTTPError, ResponsePromise} from "ky"
import {z} from "zod";

const api = ky.create({prefixUrl: config.auth_location});

export const back_post = async (endpoint: string, json: Object) => {
    return await api.post(endpoint, {json: json}).json()
}

export const ok_back_post = async (endpoint: string, json: Object) => {
    return (await api.post(endpoint, {json: json})).ok
}

const ApiError = z.object({
    error: z.string(),
    error_description: z.string(),
    debug_key: z.string()
})
type ApiError = z.infer<typeof ApiError>;

export const catch_api = async (e: unknown): Promise<ApiError> => {
    if (e instanceof HTTPError) {
        const err_json = await e.response.json()
        return ApiError.parse(err_json)
    } else {
        throw e
    }
}