import config from "../config"
import ky, {HTTPError, Options, ResponsePromise} from "ky"
import {z} from "zod";
import {AuthPageError} from "./error";

const api = ky.create({prefixUrl: config.auth_location});

export const back_post = async (endpoint: string, json: Object, options?: Options) => {
    return await api.post(endpoint, {json: json, ...options}).json()
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

export const err_api = async (e: unknown) => {
    const err = await catch_api(e)
    return new AuthPageError(err.error, err.error_description, err.debug_key)
}