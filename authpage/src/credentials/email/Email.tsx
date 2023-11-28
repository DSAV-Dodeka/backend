import React, {useEffect, useState} from "react";
import {back_post, err_api} from "../../functions/api"
import {confirm_succesful, register_link} from '../../loc.json'
import './Email.scss'
import Back from "../../components/Back";
import {AuthPageError} from "../../functions/error";
import Title from "../../components/Title";

const Email = () => {
    const [status, setStatus] = useState("De bevestigingslink is incorrect of verlopen. Probeer het opnieuw.")
    const [confirmed, setConfirmed] = useState(false)

    const badConfirm = () => {
        setStatus("De bevestigingslink is incorrect of verlopen. Probeer het opnieuw.")
        setConfirmed(false)
    }

    const handleRedirect = async (signal: AbortSignal) => {
        const source_params = (new URLSearchParams(window.location.search))
        const confirm_id = source_params.get("confirm_id")
        if (confirm_id === null) {
            throw new AuthPageError("bad_confirm", "No confirm_id has been set, so email cannot be confirmed!", "no_confirm_id")
        } else {
            try {
                await back_post("onboard/email/", {confirm_id}, {signal})
                return
            } catch (e) {
                throw await err_api(e)
            }
        }
    }

    useEffect(() => {
        const ac = new AbortController()

        handleRedirect(ac.signal).then(() => {
            setStatus(confirm_succesful)
            setConfirmed(true)
        }).catch((e) => {
            if (e instanceof AuthPageError) {
                if (e.debug_key === "bad_confirm_id") {
                    badConfirm()
                } else if (e.debug_key === "user_exists") {
                    setStatus("Je hebt je e-mail al bevestigd, we zijn bezig met het verwerken van je registratie.")
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
        <div className="backend_page">
            <Back />
            <Title title="E-mail bevestigen" />
            <p className="largeText">{status}</p>
            <p className="largeText">{confirmed && (<a className="regLink" href={register_link}>{register_link}</a>)}</p>
        </div>
    )
}

export default Email;




