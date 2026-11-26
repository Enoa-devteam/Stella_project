<template>
  <v-main class="blank-bg">
    <v-container fluid class="fill-height d-flex align-center flex-wrap">
      <router-view />
    </v-container>
  </v-main>
</template>

<style scoped>
/* v4 层序见 index.html：stella-app 位于 vuetify-components 之后、vuetify-utilities 之前 */
@layer stella-app {
.blank-bg {
  min-height: 100vh;
}
}
</style>
