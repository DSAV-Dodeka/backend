const production = false;

export default
{
    "auth_location": production ? "" : "http://localhost:4243",
    "client_location": production ? "" : "http://localhost:3000"
}