import React, {useEffect, useState} from "react";
import {clientRegister, decryptPass, keys} from "./Authenticate";
import config from "./config";

const Register = () => {
    const [handled, setHandled] = useState(false)
    const [redirectUrl, setRedirectUrl] = useState("")

    const handleRedirect = async () => {
        let source_params = (new URLSearchParams(window.location.search))

        let encrypted_pass = source_params.get("encrypted_pass");

        if (encrypted_pass == null ) {
            // if (source_params.get("key") !== "true") {
            //     throw Error
            // }
            const { private_key, public_key } = await keys()
            localStorage.setItem("private_key", private_key)
            const target_params = new URLSearchParams({
                "public_key": public_key,
            }).toString()
            console.log(target_params)

            setRedirectUrl(`${config.client_location}/register/redirect/?` + target_params)

            setHandled(true)
        } else {
            console.log("hi")
            const private_key = localStorage.getItem("private_key")
            const password = await decryptPass(private_key, encrypted_pass)
            localStorage.removeItem("private_key")
            console.log(pass)

            const is_ok = await clientRegister(username, password)

            // const handleSubmit = async (evt: React.FormEvent<HTMLFormElement>) => {
            //     const is_ok = await clientRegister(username, password)
            //     console.log(is_ok)
            //     const redirectUrl = `${config.auth_location}/oauth/callback?` + params.toString()
            //     window.location.assign(redirectUrl)
            // }
        }




    }

    useEffect(() => {
        if (!handled) {
            handleRedirect().catch();
        } else {
            window.location.replace(redirectUrl)
        }
    }, [handled]);

    return (
        <>
            <h1 className="title">Register</h1>
        </>
    )
}

export default Register;




