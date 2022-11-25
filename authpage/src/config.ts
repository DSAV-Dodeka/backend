const allowed_redirects: {[key: string]: ((a: string) => string)} = {
    "client:account/email/": (email: string) => `Please log in with your previous e-mail to confirm your e-mail change to ${email}.`,
    "client:account/delete/": (_) => "Please log in to confirm deleting your account.",
}


export default
{
    "auth_location": import.meta.env.VITE_AUTHPAGE_AUTH_URL,
    "client_location": import.meta.env.VITE_AUTHPAGE_CLIENT_URL,
    "allowed_redirects": allowed_redirects
}