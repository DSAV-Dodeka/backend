import React, { useState } from "react";
import {clientLogin, clientRegister} from "./Authenticate";
import config from "./config";

const Auth = () => {
    const [username, setUsername] = useState("")
    const [password, setPassword] = useState("")
    const [isRegister, setIsRegister] = useState(false)

    const handleSubmit = async (evt: React.FormEvent<HTMLFormElement>) => {
        evt.preventDefault()

        if (isRegister) {
            const is_ok = await clientRegister(username, password)
            console.log(is_ok)
        }
        // login
        else {
            let flow_id = (new URLSearchParams(window.location.search)).get("flow_id");
            if (flow_id == null) {
                console.log("No flow_id set!")
                return
            }
            const code = await clientLogin(username, password, flow_id)

            if (code === undefined || code == null) {
                console.log("No code received!")
                return
            }

            const params = new URLSearchParams({
                flow_id,
                code
            })

            const redirectUrl = `${config.auth_location}/oauth/callback?` + params.toString()
            window.location.assign(redirectUrl)
        }
    }

    return (
        <>
            <h1 className="title">Auth</h1>
            <div className="auth-form">
                <form onSubmit={handleSubmit}>
                    <div>
                        <label>Username</label>
                        <input id="username" placeholder="e-mail/username" type="text" value={username}
                               onChange={e => setUsername(e.target.value)}/>

                        <label>Password</label>
                        <input type="password" placeholder="password" value={password}
                               onChange={e => setPassword(e.target.value)} />
                        <input type='checkbox' placeholder="ja als registreren" checked={isRegister}
                               onChange={e => setIsRegister(e.target.checked)}/>
                    </div>
                    <button id="submit_button" type="submit">Inloggen</button><br />
                </form>
            </div>
        </>
    )
}

export default Auth;




