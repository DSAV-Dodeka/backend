class PrintableError {
    error: ClientError
    constructor(err_type: string, err_desc: string, debug_key?: string) {
        this.error = {err_type, err_desc, debug_key}
    }

    p() {
        console.log(JSON.stringify(this.error))
    }
}

export type ClientError = {
    "err_type": string,
    "err_desc": string,
    "debug_key"?: string
}

export const new_err = (err_type: string, err_desc: string, debug_key?: string): PrintableError => {
    return new PrintableError(err_type, err_desc, debug_key)
}
