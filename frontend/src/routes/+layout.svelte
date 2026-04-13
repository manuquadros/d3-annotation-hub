<script>
    /**
     * @typedef {Object} Props
     * @property {import('svelte').Snippet} [children]
     */

    /** @type {Props} */
    import { page } from "$app/stores";
    import { auth } from "$lib/auth.svelte";
    import AnnotationQueue from "$lib/components/AnnotationQueue.svelte";
    import ProjectSwitcher from "$lib/components/ProjectSwitcher.svelte";
    import "../styles.css";
    let { children, data } = $props();

    let isLoginPage = $derived($page.url.pathname === "/login");
</script>

<div class="layout">
    <div id="loader">
        <span></span>
    </div>

    <!-- Page wrapper start -->
    <div
        class="page-wrapper"
        data-sidebar-hidden={!data.authenticated || isLoginPage
            ? "hidden"
            : undefined}
    >
        <!-- Sticky alerts (toasts), empty container -->
        <div class="sticky-alerts"></div>

        <!-- Navbar start -->
        <div class="navbar navbar-top">
            <a href="index.php" class="navbar-brand ml-20">
                <!-- here goes your database logo -->
                <img src="digidive/img/Logo D3_1.png" alt="Annotation Hub" />
            </a>

            <a href="//www.dsmz.de/" class="navbar-brand ml-auto">
                <!-- DSMZ Logo is mandatory -->
                <img
                    src="//www.dsmz.de/fileadmin/templates/main/img/logo_en.svg"
                    alt="DSMZ"
                />
            </a>
        </div>

        {#if data.authenticated && !isLoginPage}
            <!-- Sidebar overlay -->
            <div
                class="sidebar-overlay"
                onclick={() => digidive.toggleSidebar()}
            ></div>

            <nav class="navbar navbar-bottom">
                <div class="container">
                    <button
                        class="btn btn-action active"
                        type="button"
                        onclick={(e) => digidive.toggleSidebar(e.currentTarget)}
                    ></button>

                    <ul class="breadcrumb navbar-breadcrumb">
                        <!-- Link items are optional: -->
                        <li>
                            <a href="#">Home</a>
                        </li>
                        <li>
                            <a href="#">References</a>
                        </li>
                        <li class="active" aria-current="page">
                            <a href="#">Article</a>
                        </li>
                    </ul>

                    <form
                        id="navbar-search"
                        action="/media"
                        method="get"
                        class="nav-search ml-auto"
                        style="margin: 0;"
                    >
                        <div class="input-group">
                            <input
                                type="text"
                                name="search"
                                class="form-control"
                                autocomplete="off"
                                placeholder="Search article"
                            />
                            <div class="input-group-append">
                                <button class="btn primary">
                                    <i class="ph ph-magnifying-glass"></i>
                                </button>
                            </div>
                        </div>
                    </form>
                </div>
            </nav>

            <!-- Sidebar start -->
            <div class="sidebar">
                <div class="sidebar-menu">
                    {#if data.projects.length > 0 && data.currentProjectId !== null}
                        <div class="sidebar-section">
                            <ProjectSwitcher
                                projects={data.projects}
                                currentProjectId={data.currentProjectId}
                                isAdmin={data.isAdmin}
                            />
                        </div>

                        {#if !data.isAdmin}
                            <nav class="queue-wrapper">
                                <p class="title">Annotation Queue</p>
                                <AnnotationQueue
                                    projectId={data.currentProjectId}
                                />
                            </nav>
                        {/if}

                        {#if data.isCurator}
                            <nav>
                                <p class="title">Curation</p>
                                <a
                                    class="with-icon"
                                    href="/curate?project={data.currentProjectId}"
                                >
                                    <i class="ph ph-check-square"></i>
                                    Curation Queue
                                </a>
                            </nav>
                        {/if}
                    {:else}
                        <div class="sidebar-section">
                            <p class="title">No projects assigned</p>
                        </div>
                    {/if}

                    <nav>
                        <p class="title">Management</p>
                        {#if data.isSuperuser}
                            <a class="with-icon" href="/admin">
                                <i class="ph ph-gear"></i>
                                Admin
                            </a>
                        {/if}
                        <a class="with-icon" onclick={() => auth.logout()}>
                            <i class="ph ph-sign-out"></i>
                            Log out
                        </a>
                    </nav>
                </div>
            </div>
            <!-- Sidebar end -->
        {/if}

        <!-- Content wrapper start -->
        <div class="content-wrapper">
            <!-- OPTIONAL: title-bar -->
            <div class="content-container">
                <div style="display: contents">{@render children?.()}</div>
            </div>
        </div>
        <!-- Content wrapper end -->

        <div class="page-footer">
            <div class="link-parade">
                <div class="row">
                    <div class="col">
                        <h3>Annotation Hub</h3>
                        <a href="#">About</a>
                        <a href="#">News</a>
                        <a href="#">Subscribe</a>
                    </div>
                    <div class="col">
                        <h3>Help</h3>
                        <a href="#">Q&amp;A</a>
                        <a href="#">Tutorials</a>
                        <a href="#">Contact</a>
                    </div>
                    <div class="col">
                        <h3>Social Media</h3>
                        <a href="#">
                            <span class="icon"
                                ><i class="ph ph-twitter-logo"></i></span
                            >
                            Twitter
                        </a>
                        <a href="#">
                            <span class="icon"
                                ><i class="ph ph-youtube-logo"></i></span
                            >
                            YouTube
                        </a>
                    </div>
                </div>
            </div>
            <div class="logo-parade">
                <a href="#"><img src="???" alt="???" /></a>
                <a href="#"><img src="???" alt="???" /></a>
            </div>
            <hr />
            <div class="footer">
                <span> &copy; DSMZ 2023 </span>
                <a href="#">Imprint</a>
                <a href="#">Privacy Statement</a>
                <a href="#">Copyright &amp; License</a>
                <a href="#">Sitemap</a>
            </div>
        </div>
    </div>
    <!-- Page wrapper end -->
</div>
