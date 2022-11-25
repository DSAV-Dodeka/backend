// export function binToBase64Url(byte_array: Uint8Array) {
//     const random_chrpts = Array.from(byte_array).map((num) => {
//         return String.fromCharCode(num)
//     }).join('')
//     return btoa(random_chrpts)
//         .replaceAll("/", "_").replaceAll("+", "-")
//         .replaceAll("=", "")
// }

export function base64ToBin(encoded_string: string) {
    const base64 = encoded_string
        .replace(new RegExp("_", "g"), "/")
        .replace(new RegExp("-", "g"), "+")

    const decoded = atob(base64)
    return new Uint8Array(Array.from(decoded).map((char) => {
        return char.charCodeAt(0)
    }))
}