import React, {useEffect, useState} from "react";
import {back_post, catch_api} from "./api"
import {confirm_succesful, register_link} from './loc.json'
import './Email.scss'

const Email = () => {
    const [handled, setHandled] = useState(false)
    const [status, setStatus] = useState("")
    const [confirmed, setConfirmed] = useState(false)

    const badConfirm = () => {
        setStatus("The confirmation link is incorrect or has expired. Please try again.")
        setConfirmed(false)
    }

    const handleRedirect = async () => {
        const source_params = (new URLSearchParams(window.location.search))
        const confirm_id = source_params.get("confirm_id")
        if (confirm_id === null) {
            console.log()
            badConfirm()
        } else {
            try {
                await back_post("onboard/email/", { confirm_id })
                setStatus(confirm_succesful)
                setConfirmed(true)

            } catch (e) {
                const err = await catch_api(e)
                if (err.debug_key === "bad_confirm_id") {
                    badConfirm()
                } else if (err.debug_key === "user_exists") {
                    setStatus("You have already confirmed your email. Please be patient while we process your registration.")
                    setConfirmed(true)
                } else if (e instanceof Error) {
                    throw e
                }
            }
        }

        setHandled(true)
    }

    useEffect(() => {
        if (!handled) {
            handleRedirect().catch();
        }
    }, [handled]);

    return (
        <>
            <h1 className="title">Email</h1>
            <p className="largeText">{status}</p>
            {confirmed && (<a className="regLink" href={register_link}>{register_link}</a>)}
        </>
    )
}

export default Email;



