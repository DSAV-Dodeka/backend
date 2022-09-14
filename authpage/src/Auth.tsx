import React, { useState } from "react";
import {clientLogin} from "./Authenticate";
import config from "./config";

const Auth = () => {
    const [username, setUsername] = useState("")
    const [password, setPassword] = useState("")

    const handleSubmit = async (evt: React.FormEvent<HTMLFormElement>) => {
        evt.preventDefault()


        // login
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

    return (
        <div className="page">
            <h1 className="title">Login</h1>
            <div className="auth-form">
                <form onSubmit={handleSubmit}>
                    <div>
                        <input id="username" placeholder="e-mail" type="text" value={username}
                               onChange={e => setUsername(e.target.value)}/>
                        <input type="password" placeholder="password" value={password}
                               onChange={e => setPassword(e.target.value)} />
                        <button id="submit_button" type="submit">Inloggen</button><br />
                    </div>
                    
                </form>
            </div>
        </div>
    )
}

export default Auth;




