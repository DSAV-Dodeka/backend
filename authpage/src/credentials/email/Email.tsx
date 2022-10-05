import React, {useEffect, useState} from "react";
import {back_post, err_api} from "../../functions/api"
import {confirm_succesful, register_link} from '../../loc.json'
import './Email.scss'
import {AuthPageError} from "../../functions/error";

const Email = () => {
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
            throw new AuthPageError("bad_confirm", "No confirm_id has been set, so email cannot be confirmed!", "no_confirm_id")
        } else {
            try {
                await back_post("onboard/email/", {confirm_id})
                return
            } catch (e) {
                throw await err_api(e)
            }
        }
    }

    useEffect(() => {
        const ac = new AbortController()

        handleRedirect().then(() => {
            setStatus(confirm_succesful)
            setConfirmed(true)
        }).catch((e) => {
            if (e instanceof AuthPageError) {
                if (e.debug_key === "bad_confirm_id") {
                    badConfirm()
                } else if (e.debug_key === "user_exists") {
                    setStatus("You have already confirmed your email. Please be patient while we process your registration.")
                    setConfirmed(true)
                } else {
                    console.log(e.j())
                }
            } else if (e.name === 'AbortError') {
                console.log((new AuthPageError("abort_error", "Aborted as email already confirmed!",
                    "abort_callback")).j())
            } else {
                throw e
            }
        });

        return () => {
            ac.abort()
        }
    }, []);

    return (
        <>
            <h1 className="title">Email</h1>
            <p className="largeText">{status}</p>
            {confirmed && (<a className="regLink" href={register_link}>{register_link}</a>)}
        </>
    )
}

export default Email;




